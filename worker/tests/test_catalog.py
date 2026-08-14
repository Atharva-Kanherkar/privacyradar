import pytest

from privacyradar import catalog
from privacyradar.db import connect
from privacyradar.settings import settings

pytestmark = pytest.mark.integration


def test_seed_catalog_skips_ssrf_urls(
    db_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "database_url", db_url)
    monkeypatch.setattr(
        catalog,
        "load_catalog",
        lambda: [
            {
                "slug": "evil",
                "name": "Evil Co",
                "website": "https://evil.example.test",
                "category": "consumer",
                "privacy_url": "http://127.0.0.1/privacy",
            }
        ],
    )
    assert catalog.seed_catalog() == 1
    with connect() as conn:
        companies = conn.execute("select slug from companies").fetchall()
        sources = conn.execute("select url from policy_sources").fetchall()
    assert [row["slug"] for row in companies] == ["evil"]
    assert sources == []
