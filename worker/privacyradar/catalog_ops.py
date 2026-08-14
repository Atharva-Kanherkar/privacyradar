"""Catalog YAML validation, cohort-aware seed, and health gate."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from privacyradar.catalog import load_catalog
from privacyradar.ssrf import SsrfError, classify_url

REQUIRED_FIELDS = ("slug", "name", "website", "category", "privacy_url", "region", "cohort")


class CatalogError(ValueError):
    """Invalid catalog YAML or nomination."""


def host_of(url: str) -> str:
    parsed = urlparse(url.strip())
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def fold_confusable(host: str) -> str:
    return host.replace("rn", "m")


def validate_companies(companies: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    slugs: set[str] = set()
    hosts: dict[str, str] = {}
    folded: dict[str, str] = {}
    for row in companies:
        slug = str(row.get("slug") or "")
        for field in REQUIRED_FIELDS:
            if not str(row.get(field) or "").strip():
                errors.append(f"{slug or '?'}: missing {field}")
        if not slug:
            continue
        if slug in slugs:
            errors.append(f"{slug}: duplicate slug")
        slugs.add(slug)
        privacy = str(row.get("privacy_url") or "")
        try:
            classify_url(privacy)
        except SsrfError:
            errors.append(f"{slug}: privacy_url failed SSRF checks")
        host = host_of(privacy)
        if not host:
            errors.append(f"{slug}: privacy_url has no host")
            continue
        if host in hosts:
            errors.append(f"{slug}: privacy host duplicates {hosts[host]}")
        hosts[host] = slug
        key = fold_confusable(host)
        if key in folded and folded[key] != slug:
            errors.append(f"{slug}: confusable host with {folded[key]}")
        folded[key] = slug
        if "xn--" in host and any(ord(ch) > 127 for ch in host):
            errors.append(f"{slug}: mixed punycode lookalike host")
    return errors


def validate_catalog() -> list[str]:
    return validate_companies(load_catalog())


def _id_for_host(rows: list[Any], host: str) -> str | None:
    for row in rows:
        if host_of(str(row["website"])) == host:
            return str(row["id"])
    return None


def record_request(conn: Any, *, name: str, website: str, category: str) -> str:
    host = host_of(website if "://" in website else f"https://{website}")
    if not host or host in {"localhost", "127.0.0.1", "::1"} or host.replace(".", "").isdigit():
        raise CatalogError("invalid_website")
    existing = _id_for_host(
        conn.execute("select id, website from companies").fetchall(),
        host,
    )
    prior = _id_for_host(
        conn.execute(
            """
            select id, website from company_requests
            where status in ('requested', 'accepted')
            """
        ).fetchall(),
        host,
    )
    duplicate_of = existing or prior
    status = "duplicate" if duplicate_of else "requested"
    conn.execute(
        """
        insert into company_requests (name, website, category, status, duplicate_of)
        values (%s, %s, %s, %s, %s)
        """,
        (name[:120], f"https://{host}", category[:40], status, duplicate_of),
    )
    return status


def health_report(conn: Any, *, record: bool = False) -> dict[str, Any]:
    sources = conn.execute("select count(*) as n from policy_sources where enabled").fetchone()
    healthy = conn.execute(
        """
        select count(*) as n from policy_sources
        where enabled and health_status = 'healthy'
        """
    ).fetchone()
    degraded = conn.execute(
        """
        select count(*) as n from policy_sources
        where enabled and health_status = 'degraded'
        """
    ).fetchone()
    quarantined = conn.execute(
        """
        select count(*) as n from policy_sources
        where health_status = 'quarantined'
        """
    ).fetchone()
    spans = conn.execute("select count(*) as n from evidence_spans").fetchone()
    exact = conn.execute(
        "select count(*) as n from evidence_spans where validation_result = 'exact'"
    ).fetchone()
    n_sources = int(sources["n"] if sources else 0)
    n_healthy = int(healthy["n"] if healthy else 0)
    n_spans = int(spans["n"] if spans else 0)
    n_exact = int(exact["n"] if exact else 0)
    fetch_pct = (100.0 * n_healthy / n_sources) if n_sources else 0.0
    evidence_pct = (100.0 * n_exact / n_spans) if n_spans else 0.0
    if record:
        conn.execute(
            """
            insert into catalog_health_snapshots (fetch_success_pct, evidence_valid_pct)
            values (%s, %s)
            """,
            (fetch_pct, evidence_pct),
        )
    cycles = conn.execute(
        """
        select fetch_success_pct, evidence_valid_pct
        from catalog_health_snapshots
        order by created_at desc
        limit 2
        """
    ).fetchall()
    gate = "stop"
    if len(cycles) >= 2 and all(
        float(row["fetch_success_pct"]) >= 95 and float(row["evidence_valid_pct"]) >= 98
        for row in cycles
    ):
        gate = "advance"
    companies = conn.execute("select count(*) as n from companies").fetchone()
    return {
        "companies": int(companies["n"] if companies else 0),
        "sources": n_sources,
        "healthy": n_healthy,
        "degraded": int(degraded["n"] if degraded else 0),
        "quarantined": int(quarantined["n"] if quarantined else 0),
        "fetch_success_pct": round(fetch_pct, 2),
        "evidence_valid_pct": round(evidence_pct, 2),
        "cycles_recorded": len(cycles),
        "gate": gate,
    }
