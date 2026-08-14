"""Consumer account deletion against the SQL function."""

from __future__ import annotations

from typing import Any

import psycopg


def delete_consumer(conn: psycopg.Connection[dict[str, Any]], user_id: str) -> None:
    conn.execute("select privacyradar_delete_consumer(%s)", (user_id,))
