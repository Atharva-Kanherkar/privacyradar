"""Published-only company comparison. No overall score."""

from __future__ import annotations

from typing import Any

COMPARE_DIMENSIONS = (
    "sensitive",
    "sharing",
    "purpose",
    "retention",
    "control",
    "data_collected",
)

MAX_COMPANIES = 4


def parse_company_slugs(raw: str | list[str] | None) -> tuple[list[str], bool]:
    parts: list[str] = []
    if isinstance(raw, list):
        for item in raw:
            parts.extend(item.split(","))
    elif isinstance(raw, str):
        parts = raw.split(",")
    seen: list[str] = []
    for part in parts:
        slug = part.strip().lower()
        if slug and slug not in seen:
            seen.append(slug)
    truncated = len(seen) > MAX_COMPANIES
    return seen[:MAX_COMPANIES], truncated


def _latest_claims(conn: Any, company_id: str) -> list[dict[str, Any]]:
    return list(
        conn.execute(
            """
            select
              pc.claim_key,
              pc.category,
              pc.attribute,
              pc.polarity,
              pc.quote,
              pc.snapshot_id,
              pr.taxonomy_version,
              pr.revision_n
            from published_claims pc
            join publication_revisions pr on pr.id = pc.revision_id
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
    )


def build_comparison(conn: Any, slugs: list[str], *, truncated: bool = False) -> dict[str, Any]:
    if len(slugs) < 2:
        return {
            "status": "need_selection",
            "companies": [],
            "dimensions": [],
            "truncated": truncated,
        }
    rows = conn.execute(
        """
        select
          c.id,
          c.slug,
          c.name,
          s.region,
          s.health_status,
          s.last_success_at,
          exists(
            select 1 from change_events e
            where e.company_id = c.id and e.publication_state = 'corrected'
          ) as corrected
        from companies c
        left join policy_sources s
          on s.company_id = c.id and s.kind = 'privacy'
        where c.slug = any(%s)
        """,
        (slugs,),
    ).fetchall()
    by_slug = {str(row["slug"]): row for row in rows}
    companies: list[dict[str, Any]] = []
    taxonomies: set[str] = set()
    regions: set[str] = set()
    for slug in slugs:
        row = by_slug.get(slug)
        if row is None:
            companies.append(
                {
                    "slug": slug,
                    "name": slug,
                    "region": None,
                    "health": None,
                    "corrected": False,
                    "has_publication": False,
                    "taxonomy_version": None,
                    "claims": [],
                }
            )
            continue
        claims = [dict(item) for item in _latest_claims(conn, str(row["id"]))]
        taxonomy = str(claims[0]["taxonomy_version"]) if claims else None
        if taxonomy:
            taxonomies.add(taxonomy)
        region = row["region"]
        if region:
            regions.add(str(region))
        companies.append(
            {
                "slug": str(row["slug"]),
                "name": str(row["name"]),
                "region": str(region) if region else None,
                "health": str(row["health_status"]) if row["health_status"] else None,
                "last_verified_at": row["last_success_at"],
                "corrected": bool(row["corrected"]),
                "has_publication": bool(claims),
                "taxonomy_version": taxonomy,
                "claims": claims,
            }
        )
    region_mismatch = len(regions) > 1
    status = "not_comparable" if len(taxonomies) > 1 else "comparable"
    dimensions: list[dict[str, Any]] = []
    if status == "comparable":
        for category in COMPARE_DIMENSIONS:
            cells = []
            for company in companies:
                match = next(
                    (claim for claim in company["claims"] if claim["category"] == category),
                    None,
                )
                if match is None:
                    cells.append(
                        {
                            "slug": company["slug"],
                            "state": "not_found_in_evidence",
                            "favorable": False,
                        }
                    )
                else:
                    cells.append(
                        {
                            "slug": company["slug"],
                            "state": "found",
                            "attribute": match["attribute"],
                            "polarity": match["polarity"],
                            "quote": match["quote"],
                            "claim_key": match["claim_key"],
                            "revision_n": match["revision_n"],
                            "snapshot_id": str(match["snapshot_id"]),
                        }
                    )
            dimensions.append({"category": category, "cells": cells})
    payload: dict[str, Any] = {
        "status": status,
        "region_mismatch": region_mismatch,
        "taxonomy_version": next(iter(taxonomies), None),
        "truncated": truncated,
        "companies": [
            {key: value for key, value in company.items() if key != "claims"}
            for company in companies
        ],
        "dimensions": dimensions,
    }
    return payload
