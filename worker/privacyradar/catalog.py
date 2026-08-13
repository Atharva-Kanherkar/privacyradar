from __future__ import annotations

from pathlib import Path

import yaml
from psycopg.rows import dict_row

from privacyradar.db import connect
from privacyradar.settings import settings


def load_catalog(path: Path | None = None) -> list[dict]:
    catalog_path = path or settings.catalog_path
    data = yaml.safe_load(catalog_path.read_text())
    return list(data["companies"])


def seed_catalog() -> int:
    companies = load_catalog()
    with connect() as conn:
        conn.row_factory = dict_row
        with conn.cursor() as cur:
            for row in companies:
                cur.execute(
                    """
                    insert into companies (slug, name, website, category)
                    values (%s, %s, %s, %s)
                    on conflict (slug) do update
                      set name = excluded.name,
                          website = excluded.website,
                          category = excluded.category
                    returning id
                    """,
                    (row["slug"], row["name"], row["website"], row["category"]),
                )
                company_id = cur.fetchone()["id"]
                cur.execute(
                    """
                    insert into policy_sources (company_id, kind, url, region)
                    values (%s, 'privacy', %s, 'global')
                    on conflict (company_id, kind, region) do update
                      set url = excluded.url,
                          enabled = true
                    """,
                    (company_id, row["privacy_url"]),
                )
        conn.commit()
    return len(companies)
