from __future__ import annotations

import argparse
import sys

from privacyradar.catalog import seed_catalog
from privacyradar.migrate import migrate
from privacyradar.pipeline import crawl_all, extract_missing
from privacyradar.settings import settings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="privacyradar")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("migrate", help="Apply numbered forward-only SQL migrations")
    sub.add_parser("seed", help="Load worker/data/catalog.yaml into Postgres")
    sub.add_parser("crawl", help="Fetch every enabled policy URL once")
    sub.add_parser(
        "extract",
        help="Backfill OpenAI extraction on snapshots that have no practices yet",
    )

    args = parser.parse_args(argv)
    if args.cmd == "migrate":
        applied = migrate(settings.database_url)
        if applied:
            print("applied " + ", ".join(applied))
        else:
            print("already at head")
        return 0
    if args.cmd == "seed":
        n = seed_catalog()
        print(f"seeded {n} companies")
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
