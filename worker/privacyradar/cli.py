from __future__ import annotations

import argparse
import sys

from privacyradar.catalog import seed_catalog
from privacyradar.db import connect
from privacyradar.migrate import migrate
from privacyradar.pipeline import crawl_all, extract_missing
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
    sub.add_parser("crawl", help="Fetch every enabled policy URL once")
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
    if args.cmd == "crawl":
        for line in crawl_all():
            print(line)
        return 0
    if args.cmd == "extract":
        for line in extract_missing():
            print(line)
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
