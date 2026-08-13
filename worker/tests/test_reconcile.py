from __future__ import annotations

import psycopg
import pytest
from psycopg.rows import dict_row

from privacyradar.reconcile import reconcile_observations

pytestmark = pytest.mark.integration


def test_reconcile_is_idempotent_after_migrate(empty_database_url: str) -> None:
    from privacyradar.migrate import migrate

    migrate(empty_database_url)
    with psycopg.connect(empty_database_url, row_factory=dict_row) as conn:
        first = reconcile_observations(conn)
        conn.commit()
        second = reconcile_observations(conn)
        conn.commit()
    assert second.observations_created == 0
    assert second.attempts_created == 0
    assert second.current_pointers_set == 0
    assert first.sources == second.sources
