from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Json

from privacyradar.settings import settings


@contextmanager
def connect() -> Iterator[psycopg.Connection[dict[str, Any]]]:
    with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
        yield conn


def fetch_enabled_sources(conn: psycopg.Connection[dict[str, Any]]) -> list[dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            select
              s.id as source_id,
              s.url,
              s.kind,
              s.region,
              c.id as company_id,
              c.slug,
              c.name
            from policy_sources s
            join companies c on c.id = s.company_id
            where s.enabled = true
            order by c.name
            """
        )
        return list(cur.fetchall())


def snapshot_has_extraction(
    conn: psycopg.Connection[dict[str, Any]], snapshot_id: str
) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "select 1 from extractions where snapshot_id = %s limit 1",
            (snapshot_id,),
        )
        return cur.fetchone() is not None


def latest_snapshot(
    conn: psycopg.Connection[dict[str, Any]], source_id: str
) -> dict[str, Any] | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            select * from snapshots
            where source_id = %s
            order by fetched_at desc
            limit 1
            """,
            (source_id,),
        )
        return cur.fetchone()


def insert_snapshot(
    conn: psycopg.Connection[dict[str, Any]],
    *,
    source_id: str,
    status: int | None,
    content_type: str,
    html: str,
    markdown: str,
    doc_hash: str,
    section_hashes: dict[str, str],
    error: str | None,
) -> dict[str, Any]:
    with conn.cursor() as cur:
        cur.execute(
            """
            insert into snapshots (
              source_id, http_status, content_type, raw_html, markdown,
              doc_hash, section_hashes, fetch_error
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s)
            on conflict (source_id, doc_hash) do update
              set fetched_at = now(),
                  http_status = excluded.http_status,
                  fetch_error = excluded.fetch_error
            returning *
            """,
            (
                source_id,
                status,
                content_type,
                html,
                markdown,
                doc_hash,
                Json(section_hashes),
                error,
            ),
        )
        row = cur.fetchone()
    conn.commit()
    assert row is not None
    return row


def insert_extraction(
    conn: psycopg.Connection[dict[str, Any]],
    *,
    snapshot_id: str,
    model: str,
    practices: dict[str, Any],
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            insert into extractions (snapshot_id, model, practices)
            values (%s, %s, %s)
            """,
            (snapshot_id, model, Json(practices)),
        )
    conn.commit()


def insert_change_event(
    conn: psycopg.Connection[dict[str, Any]],
    *,
    company_id: str,
    source_id: str,
    from_snapshot: str | None,
    to_snapshot: str,
    materiality: str,
    headline: str,
    summary: str,
    data_types_added: list[str],
    data_types_removed: list[str],
    quotes: list[dict[str, Any]],
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            insert into change_events (
              company_id, source_id, from_snapshot, to_snapshot,
              materiality, headline, summary,
              data_types_added, data_types_removed, quotes
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                company_id,
                source_id,
                from_snapshot,
                to_snapshot,
                materiality,
                headline,
                summary,
                data_types_added,
                data_types_removed,
                Json(quotes),
            ),
        )
    conn.commit()
