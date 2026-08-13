from __future__ import annotations

from collections.abc import Callable
from typing import Any

from privacyradar import db
from privacyradar.analyze import extract_practices, judge_materiality
from privacyradar.crawl import FetchResult, fetch_url, polite_pause
from privacyradar.hashing import changed_sections, doc_hash, section_hashes
from privacyradar.schema import MaterialityJudgement, PracticeDocument
from privacyradar.settings import settings

FetchFn = Callable[[str], FetchResult]
ExtractFn = Callable[[str, str], tuple[PracticeDocument, str]]
JudgeFn = Callable[[str, str, str, list[str]], tuple[MaterialityJudgement, str]]


def process_source(
    source: dict[str, Any],
    *,
    fetch: FetchFn | None = None,
    extract: ExtractFn | None = None,
    judge: JudgeFn | None = None,
) -> str:
    """Fetch one policy URL. LLM only if the content hash changed."""
    fetch_fn = fetch if fetch is not None else fetch_url
    extract_fn = extract if extract is not None else extract_practices
    judge_fn = judge if judge is not None else judge_materiality
    fetched = fetch_fn(source["url"])
    markdown = fetched.markdown
    digest = doc_hash(markdown) if markdown else "empty"
    sections = section_hashes(markdown) if markdown else {}

    with db.connect() as conn:
        previous = db.latest_snapshot(conn, source["source_id"])
        if previous and previous["doc_hash"] == digest and not fetched.error:
            if (
                settings.openai_api_key
                and previous.get("markdown")
                and not db.snapshot_has_extraction(conn, previous["id"])
            ):
                doc, model = extract_fn(source["name"], previous["markdown"])
                db.insert_extraction(
                    conn,
                    snapshot_id=previous["id"],
                    model=model,
                    practices=doc.model_dump(),
                )
                return (
                    f"{source['slug']}: unchanged hash, backfilled "
                    f"{len(doc.practices)} practices"
                )
            return f"{source['slug']}: unchanged ({digest[:10]})"

        snapshot = db.insert_snapshot(
            conn,
            source_id=source["source_id"],
            status=fetched.status,
            content_type=fetched.content_type,
            html=fetched.html,
            markdown=markdown,
            doc_hash=digest,
            section_hashes=sections,
            error=fetched.error,
        )

        if fetched.error or not markdown:
            return f"{source['slug']}: fetch failed ({fetched.error or fetched.status})"

        first_seen = previous is None or previous.get("markdown") in (None, "")
        if first_seen:
            if not settings.openai_api_key:
                return f"{source['slug']}: first snapshot stored, skipped LLM (no key)"
            doc, model = extract_fn(source["name"], markdown)
            db.insert_extraction(
                conn,
                snapshot_id=snapshot["id"],
                model=model,
                practices=doc.model_dump(),
            )
            return f"{source['slug']}: first extract ({len(doc.practices)} practices)"

        if not settings.openai_api_key:
            return f"{source['slug']}: hash changed, skipped LLM (no key)"

        assert previous is not None
        changed = changed_sections(previous.get("section_hashes") or {}, sections)
        judgement, _model = judge_fn(
            source["name"],
            previous.get("markdown") or "",
            markdown,
            changed,
        )
        if judgement.materiality == "material":
            doc, model = extract_fn(source["name"], markdown)
            db.insert_extraction(
                conn,
                snapshot_id=snapshot["id"],
                model=model,
                practices=doc.model_dump(),
            )
        db.insert_change_event(
            conn,
            company_id=source["company_id"],
            source_id=source["source_id"],
            from_snapshot=str(previous["id"]),
            to_snapshot=str(snapshot["id"]),
            materiality=judgement.materiality,
            headline=judgement.headline or f"{source['name']} privacy policy updated",
            summary=judgement.summary,
            data_types_added=list(judgement.data_types_added),
            data_types_removed=list(judgement.data_types_removed),
            quotes=[q.model_dump() for q in judgement.quotes],
        )
        detail = judgement.headline or judgement.reason
        return f"{source['slug']}: {judgement.materiality} - {detail}"


def crawl_all() -> list[str]:
    results: list[str] = []
    with db.connect() as conn:
        sources = db.fetch_enabled_sources(conn)
    for i, source in enumerate(sources):
        if i:
            polite_pause()
        results.append(process_source(source))
    return results


def extract_missing() -> list[str]:
    """Run OpenAI on stored snapshots that were saved before a key existed."""
    results: list[str] = []
    with db.connect() as conn:
        sources = db.fetch_enabled_sources(conn)
        for source in sources:
            snapshot = db.latest_snapshot(conn, source["source_id"])
            if not snapshot or not snapshot.get("markdown"):
                results.append(f"{source['slug']}: no snapshot")
                continue
            if db.snapshot_has_extraction(conn, snapshot["id"]):
                results.append(f"{source['slug']}: already extracted")
                continue
            if not settings.openai_api_key:
                results.append(f"{source['slug']}: skipped (no key)")
                continue
            try:
                doc, model = extract_practices(source["name"], snapshot["markdown"])
            except Exception as exc:
                results.append(f"{source['slug']}: extract failed ({exc})")
                continue
            db.insert_extraction(
                conn,
                snapshot_id=snapshot["id"],
                model=model,
                practices=doc.model_dump(),
            )
            results.append(f"{source['slug']}: {len(doc.practices)} practices ({model})")
    return results
