from __future__ import annotations

import psycopg
import pytest
from psycopg.rows import dict_row

pytestmark = pytest.mark.integration


def test_kill_switches_exist_and_assistant_is_off(db_url: str) -> None:
    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        rows = conn.execute(
            "select key, enabled from product_switches order by key"
        ).fetchall()
    by_key = {row["key"]: bool(row["enabled"]) for row in rows}
    assert "publication" in by_key
    assert "notifications" in by_key
    assert by_key["assistant"] is False
