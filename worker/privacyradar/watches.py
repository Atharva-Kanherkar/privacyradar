"""Watchlist mutations. User identity is always a session-derived argument."""

from __future__ import annotations

from typing import Any

import psycopg

ALLOWED_SOURCES = frozenset({"company_page", "radar_onboarding", "resume"})


class WatchError(ValueError):
    """Caller supplied an untrusted user identifier or invalid watch input."""


def session_user_id(*, session_user_id: str | None, body: dict[str, Any] | None = None) -> str:
    payload = body or {}
    if "userId" in payload or "user_id" in payload:
        raise WatchError("user id must come from session")
    if not session_user_id:
        raise WatchError("missing session")
    return session_user_id


def follow(
    conn: psycopg.Connection[dict[str, Any]],
    *,
    user_id: str,
    company_id: str,
    source: str,
) -> None:
    if source not in ALLOWED_SOURCES:
        raise WatchError("invalid source")
    conn.execute(
        """
        insert into watches (user_id, company_id, status, source)
        values (%s, %s, 'active', %s)
        on conflict (user_id, company_id) do update
          set status = 'active',
              source = excluded.source,
              updated_at = now()
        """,
        (user_id, company_id, source),
    )
    conn.execute(
        """
        insert into product_events (user_id, name, company_id)
        values (%s, 'follow', %s)
        """,
        (user_id, company_id),
    )


def unfollow(
    conn: psycopg.Connection[dict[str, Any]],
    *,
    user_id: str,
    company_id: str,
) -> None:
    conn.execute(
        """
        update watches
        set status = 'unwatched', updated_at = now()
        where user_id = %s and company_id = %s
        """,
        (user_id, company_id),
    )
    conn.execute(
        """
        insert into product_events (user_id, name, company_id)
        values (%s, 'unfollow', %s)
        """,
        (user_id, company_id),
    )


def list_radar_events(
    conn: psycopg.Connection[dict[str, Any]],
    *,
    user_id: str,
    limit: int = 40,
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        select
          e.id,
          e.headline,
          e.summary,
          e.materiality,
          e.published_at,
          e.publication_state,
          c.slug,
          c.name
        from change_events e
        join companies c on c.id = e.company_id
        join watches w on w.company_id = c.id
        where w.user_id = %s
          and w.status = 'active'
          and e.publication_state = 'published'
          and e.materiality = 'material'
        order by e.published_at desc, e.id desc
        limit %s
        """,
        (user_id, limit),
    ).fetchall()
    return list(rows)


def list_active_watches(
    conn: psycopg.Connection[dict[str, Any]],
    *,
    user_id: str,
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        select w.company_id, w.status, w.source, c.slug, c.name, c.category
        from watches w
        join companies c on c.id = w.company_id
        where w.user_id = %s and w.status = 'active'
        order by c.name
        """,
        (user_id,),
    ).fetchall()
    return list(rows)
