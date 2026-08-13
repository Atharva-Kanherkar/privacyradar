from __future__ import annotations

import argparse
import sys

from privacyradar.catalog import seed_catalog
from privacyradar.db import connect
from privacyradar.migrate import migrate
from privacyradar.pipeline import crawl_all, extract_missing
from privacyradar.reconcile import format_report, reconcile_observations
from privacyradar.settings import settings
from privacyradar.testing.persist import seed_public_fixtures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="privacyradar")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("migrate", help="Apply numbered forward-only SQL migrations")
    sub.add_parser("seed", help="Load worker/data/catalog.yaml into Postgres")
    sub.add_parser(
        "seed-fixtures",
        help="Load deterministic public fixtures for local and browser tests",
    )
    sub.add_parser(
        "reconcile-observations",
        help="Idempotent backfill of observations from existing snapshots",
    )
    retry = sub.add_parser("source-retry", help="Replay a quarantined or stalled source")
    retry.add_argument("source_id")
    retry.add_argument("--actor", required=True)
    disable = sub.add_parser("source-disable", help="Disable a source and cancel pending jobs")
    disable.add_argument("source_id")
    disable.add_argument("--actor", required=True)
    enable = sub.add_parser("source-enable", help="Re-enable a source")
    enable.add_argument("source_id")
    enable.add_argument("--actor", required=True)
    sub.add_parser("fetch-stats", help="Print fetch queue counts without URLs")
    sub.add_parser(
        "extract",
        help="Backfill OpenAI extraction on snapshots that have no practices yet",
    )

    args = parser.parse_args(argv)
    if args.cmd == "migrate":
        try:
            applied = migrate(settings.database_url)
        except Exception as exc:
            print(f"migrate failed: {type(exc).__name__}", file=sys.stderr)
            return 1
        if applied:
            print("applied " + ", ".join(applied))
        else:
            print("already at head")
        return 0
    if args.cmd == "seed":
        n = seed_catalog()
        print(f"seeded {n} companies")
        return 0
    if args.cmd == "seed-fixtures":
        try:
            with connect() as conn:
                n = seed_public_fixtures(conn)
                conn.commit()
        except Exception as exc:
            print(f"seed-fixtures failed: {type(exc).__name__}", file=sys.stderr)
            return 1
        print(f"seeded {n} fixture companies")
        return 0
    if args.cmd == "reconcile-observations":
        try:
            with connect() as conn:
                report = reconcile_observations(conn)
                conn.commit()
        except Exception as exc:
            print(f"reconcile-observations failed: {type(exc).__name__}", file=sys.stderr)
            return 1
        print(format_report(report))
        return 0
    if args.cmd == "crawl":
        for line in crawl_all():
            print(line)
        return 0
    if args.cmd == "source-retry":
        from privacyradar.operator import source_retry

        try:
            with connect() as conn:
                action_id = source_retry(conn, args.source_id, actor=args.actor)
                conn.commit()
        except Exception as exc:
            print(f"source-retry failed: {type(exc).__name__}", file=sys.stderr)
            return 1
        print(f"retry queued {action_id}")
        return 0
    if args.cmd == "source-disable":
        from privacyradar.operator import source_disable

        try:
            with connect() as conn:
                action_id = source_disable(conn, args.source_id, actor=args.actor)
                conn.commit()
        except Exception as exc:
            print(f"source-disable failed: {type(exc).__name__}", file=sys.stderr)
            return 1
        print(f"disabled {action_id}")
        return 0
    if args.cmd == "source-enable":
        from privacyradar.operator import source_enable

        try:
            with connect() as conn:
                action_id = source_enable(conn, args.source_id, actor=args.actor)
                conn.commit()
        except Exception as exc:
            print(f"source-enable failed: {type(exc).__name__}", file=sys.stderr)
            return 1
        print(f"enabled {action_id}")
        return 0
    if args.cmd == "fetch-stats":
        from privacyradar.leases import fetch_stats

        try:
            with connect() as conn:
                stats = fetch_stats(conn)
        except Exception as exc:
            print(f"fetch-stats failed: {type(exc).__name__}", file=sys.stderr)
            return 1
        for key, value in stats.items():
            print(f"{key}={value}")
        return 0
    if args.cmd == "extract":
        for line in extract_missing():
            print(line)
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
