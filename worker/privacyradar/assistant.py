"""Company-scoped cited assistant. No citation means no factual answer."""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import UTC, datetime
from typing import Any

from privacyradar.settings import settings

logger = logging.getLogger(__name__)

DAILY_LIMIT = 10
OUT_OF_SCOPE = re.compile(
    r"\b(weather|stock|sue|illegal|lawyer|other company|competitor)\b",
    re.IGNORECASE,
)


def identity_hash(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def assistant_enabled(conn: Any) -> bool:
    row = conn.execute("select enabled from product_switches where key = 'assistant'").fetchone()
    return bool(row and row["enabled"])


def retrieve_published(conn: Any, company_id: str, question: str) -> list[dict[str, Any]]:
    tokens = {part.lower() for part in re.findall(r"[a-z0-9]{3,}", question.lower())}
    rows = conn.execute(
        """
        select
          pc.claim_key,
          pc.category,
          pc.attribute,
          pc.polarity,
          pc.quote,
          pc.snapshot_id,
          pr.revision_n,
          c.slug
        from published_claims pc
        join publication_revisions pr on pr.id = pc.revision_id
        join companies c on c.id = pr.company_id
        where pr.company_id = %s
          and pr.state = 'published'
          and not exists (
            select 1 from publication_revisions rb where rb.rolls_back_id = pr.id
          )
          and pr.revision_n = (
            select coalesce(max(pr2.revision_n), 0)
            from publication_revisions pr2
            where pr2.company_id = %s
              and pr2.state = 'published'
              and not exists (
                select 1 from publication_revisions rb where rb.rolls_back_id = pr2.id
              )
          )
        """,
        (company_id, company_id),
    ).fetchall()
    scored: list[tuple[int, dict[str, Any]]] = []
    for row in rows:
        blob = f"{row['category']} {row['attribute']} {row['quote']}".lower()
        hits = sum(1 for token in tokens if re.search(rf"\b{re.escape(token)}\b", blob))
        if hits:
            scored.append((hits, dict(row)))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in scored[:8]]


def _consume_quota(conn: Any, identity: str) -> int:
    today = datetime.now(UTC).date()
    conn.execute(
        """
        insert into assistant_usage (identity_hash, day, count)
        values (%s, %s, 1)
        on conflict (identity_hash, day) do update
          set count = assistant_usage.count + 1,
              updated_at = now()
        """,
        (identity, today),
    )
    row = conn.execute(
        """
        select count from assistant_usage
        where identity_hash = %s and day = %s
        """,
        (identity, today),
    ).fetchone()
    return int(row["count"] if row else 1)


def fake_answer(question: str, retrieved: list[dict[str, Any]]) -> dict[str, Any]:
    if OUT_OF_SCOPE.search(question):
        return {"status": "refused", "reason": "out_of_scope", "text": "", "citations": []}
    if not retrieved:
        return {
            "status": "refused",
            "reason": "insufficient_evidence",
            "text": "",
            "citations": [],
        }
    top = retrieved[0]
    text = f"We found published evidence: {top['quote']}"
    return {
        "status": "answered",
        "reason": None,
        "text": text,
        "citations": [
            {
                "claim_key": top["claim_key"],
                "quote": top["quote"],
                "snapshot_id": str(top["snapshot_id"]),
                "revision_n": int(top["revision_n"]),
                "slug": top["slug"],
            }
        ],
    }


def validate_answer(payload: dict[str, Any], retrieved: list[dict[str, Any]]) -> dict[str, Any]:
    allowed = {str(row["claim_key"]) for row in retrieved}
    citations = list(payload.get("citations") or [])
    if any(str(item.get("claim_key")) not in allowed for item in citations):
        return {
            "status": "refused",
            "reason": "invalid_citation",
            "text": "",
            "citations": [],
        }
    if payload.get("status") == "answered" and not citations:
        return {
            "status": "refused",
            "reason": "insufficient_evidence",
            "text": "",
            "citations": [],
        }
    return payload


def ask(
    conn: Any,
    *,
    slug: str,
    question: str,
    identity: str,
) -> dict[str, Any]:
    if settings.assistant_provider != "fake":
        logger.info("assistant_provider_blocked")
        return {
            "status": "disabled",
            "reason": "provider_not_allowed",
            "text": "",
            "citations": [],
        }
    if not assistant_enabled(conn):
        return {"status": "disabled", "reason": "assistant_off", "text": "", "citations": []}
    company = conn.execute("select id, slug from companies where slug = %s", (slug,)).fetchone()
    if company is None:
        return {"status": "refused", "reason": "unknown_company", "text": "", "citations": []}
    used = _consume_quota(conn, identity)
    if used > DAILY_LIMIT:
        return {"status": "rate_limited", "reason": "daily_limit", "text": "", "citations": []}
    retrieved = retrieve_published(conn, str(company["id"]), question)
    if any(str(row["slug"]) != slug for row in retrieved):
        return {"status": "refused", "reason": "cross_company", "text": "", "citations": []}
    raw = fake_answer(question, retrieved)
    return validate_answer(raw, retrieved)


GOLDEN = (
    {
        "slug": "signal",
        "question": "Does Signal collect email addresses?",
        "expect": "answered",
    },
    {
        "slug": "signal",
        "question": "What is the weather in Berlin?",
        "expect": "refused",
    },
    {
        "slug": "signal",
        "question": "Should I sue them?",
        "expect": "refused",
    },
)


def run_eval(conn: Any) -> dict[str, Any]:
    answered = 0
    refused = 0
    bad = 0
    for case in GOLDEN:
        company = conn.execute(
            "select id from companies where slug = %s", (case["slug"],)
        ).fetchone()
        if company is None:
            bad += 1
            continue
        retrieved = retrieve_published(conn, str(company["id"]), case["question"])
        payload = validate_answer(fake_answer(case["question"], retrieved), retrieved)
        if payload["status"] != case["expect"]:
            bad += 1
        if payload["status"] == "answered":
            answered += 1
            if not payload["citations"]:
                bad += 1
        if payload["status"] == "refused":
            refused += 1
    gate = "pass" if bad == 0 and answered >= 1 and refused >= 1 else "fail"
    return {
        "answered": answered,
        "refused": refused,
        "mismatches": bad,
        "gate": gate,
    }
