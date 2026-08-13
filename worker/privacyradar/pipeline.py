from __future__ import annotations

from collections.abc import Callable
from typing import Any

from privacyradar import db
from privacyradar.analyze import extract_practices, judge_materiality
from privacyradar.crawl import FetchResult, fetch_url
from privacyradar.hashing import changed_sections
from privacyradar.leases import drain_once
from privacyradar.observe import observe_source
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
    """Fetch one policy URL. Hash comparison never uses a model."""
    fetch_fn = fetch if fetch is not None else fetch_url
    extract_fn = extract if extract is not None else extract_practices
    judge_fn = judge if judge is not None else judge_materiality
    fetched = fetch_fn(source["url"])

    with db.connect() as conn:
        observed = observe_source(conn, source, fetched)
        conn.commit()

    if observed.outcome == "failed":
        return observed.message

    if observed.outcome == "deduped":
        if settings.openai_api_key and observed.snapshot_id:
            with db.connect() as conn:
                previous = db.snapshot_by_id(conn, observed.snapshot_id)
                if (
                    previous
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
        return observed.message

    if not settings.openai_api_key:
        if observed.document_change_id is None:
            return f"{source['slug']}: first snapshot stored, skipped LLM (no key)"
        return f"{source['slug']}: hash changed, skipped LLM (no key)"

    with db.connect() as conn:
        snapshot = db.snapshot_by_id(conn, observed.snapshot_id or "")
        previous = None
        if snapshot is None:
            return observed.message
        if observed.document_change_id is None:
            doc, model = extract_fn(source["name"], snapshot["markdown"])
            db.insert_extraction(
                conn,
                snapshot_id=snapshot["id"],
                model=model,
                practices=doc.model_dump(),
            )
            return f"{source['slug']}: first extract ({len(doc.practices)} practices)"

        previous_id = conn.execute(
            "select previous_snapshot_id from observations where id = %s",
            (observed.observation_id,),
        ).fetchone()
        if previous_id and previous_id["previous_snapshot_id"]:
            previous = db.snapshot_by_id(conn, str(previous_id["previous_snapshot_id"]))
        if previous is None:
            return observed.message
        changed = changed_sections(
            previous.get("section_hashes") or {}, snapshot.get("section_hashes") or {}
        )
        judgement, _model = judge_fn(
            source["name"],
            previous.get("markdown") or "",
            snapshot["markdown"],
            changed,
        )
        if judgement.materiality == "material":
            doc, model = extract_fn(source["name"], snapshot["markdown"])
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


def crawl_all(fetch: FetchFn | None = None) -> list[str]:
    with db.connect() as conn:
        results = drain_once(conn, fetch=fetch)
        conn.commit()
        return results


def extract_missing() -> list[str]:
    """Run OpenAI on stored snapshots that were saved before a key existed."""
    results: list[str] = []
    with db.connect() as conn:
        sources = db.fetch_enabled_sources(conn)
        for source in sources:
            snapshot = db.current_snapshot(conn, source["source_id"])
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
                results.append(f"{source['slug']}: extract failed ({type(exc).__name__})")
                continue
            db.insert_extraction(
                conn,
                snapshot_id=snapshot["id"],
                model=model,
                practices=doc.model_dump(),
            )
            results.append(f"{source['slug']}: {len(doc.practices)} practices ({model})")
    return results
