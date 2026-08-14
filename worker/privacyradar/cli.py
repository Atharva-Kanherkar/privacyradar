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
    sub.add_parser(
        "crawl",
        help="Claim due fetch jobs via Postgres even when Redis is down",
    )
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
    sub.add_parser(
        "eval-extract",
        help="Run the synthetic extraction golden suite (no live model)",
    )
    extract_obs = sub.add_parser(
        "extract-observation",
        help="Extract candidate claims for one observation (live model if keyed)",
    )
    extract_obs.add_argument("observation_id")
    publish = sub.add_parser("publish-run", help="Publish validated claims from an extraction run")
    publish.add_argument("run_id")
    publish.add_argument("--actor", required=True)
    publish.add_argument("--change-event-id")
    publish_ev = sub.add_parser("publish-event", help="Publish a review_pending change event")
    publish_ev.add_argument("event_id")
    publish_ev.add_argument("--actor", required=True)
    reject = sub.add_parser("reject-event", help="Reject a change event")
    reject.add_argument("event_id")
    reject.add_argument("--actor", required=True)
    reject.add_argument("--reason", required=True)
    rollback = sub.add_parser("rollback-revision", help="Roll back a publication revision")
    rollback.add_argument("revision_id")
    rollback.add_argument("--actor", required=True)
    rollback.add_argument("--reason", required=True)
    corr_s = sub.add_parser("correction-submit", help="Submit a correction against a revision")
    corr_s.add_argument("--company-id", required=True)
    corr_s.add_argument("--revision-id", required=True)
    corr_s.add_argument("--note", required=True)
    corr_s.add_argument("--actor", required=True)
    corr_r = sub.add_parser("correction-resolve", help="Resolve a correction")
    corr_r.add_argument("correction_id")
    corr_r.add_argument("--actor", required=True)
    corr_r.add_argument("--decision", required=True, choices=("corrected", "declined"))
    corr_r.add_argument("--note", required=True)
    sub.add_parser("publish-stats", help="Print publication queue counts without quotes")
    sub.add_parser("eval-materiality", help="Run the synthetic materiality corpus (no live model)")

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
    if args.cmd == "eval-extract":
        from privacyradar import eval_runner

        try:
            eval_report = eval_runner.evaluate_golden()
        except Exception as exc:
            print(f"eval-extract failed: {type(exc).__name__}", file=sys.stderr)
            return 1
        print(eval_runner.format_report(eval_report))
        if not eval_runner.gates_pass(eval_report):
            return 1
        return 0
    if args.cmd == "extract-observation":
        from privacyradar.extract import extract_observation
        from privacyradar.extract_live import default_extractor

        try:
            extractor = default_extractor()
            with connect() as conn:
                outcome = extract_observation(conn, args.observation_id, extractor)
                conn.commit()
        except Exception as exc:
            print(f"extract-observation failed: {type(exc).__name__}", file=sys.stderr)
            return 1
        if outcome is None:
            print("extract-observation refused")
            return 1
        print(
            f"run_id={outcome.run_id} n_claims={outcome.n_claims} "
            f"n_unsupported={outcome.n_unsupported} latency_ms={outcome.latency_ms} "
            f"cost_usd={outcome.cost_usd} model={outcome.model}"
        )
        return 0
    if args.cmd == "publish-run":
        from privacyradar.publication import publish_run

        try:
            with connect() as conn:
                result = publish_run(
                    conn, args.run_id, actor=args.actor, change_event_id=args.change_event_id
                )
                conn.commit()
        except Exception as exc:
            print(f"publish-run failed: {type(exc).__name__}", file=sys.stderr)
            return 1
        print(
            f"revision_id={result.revision_id} revision_n={result.revision_n} "
            f"n_claims={result.n_claims}"
        )
        return 0
    if args.cmd == "reject-event":
        from privacyradar.publication import reject_event

        try:
            with connect() as conn:
                reject_event(conn, args.event_id, actor=args.actor, reason=args.reason)
                conn.commit()
        except Exception as exc:
            print(f"reject-event failed: {type(exc).__name__}", file=sys.stderr)
            return 1
        print("rejected")
        return 0
    if args.cmd == "publish-event":
        from privacyradar.publication import publish_event

        try:
            with connect() as conn:
                publish_event(conn, args.event_id, actor=args.actor)
                conn.commit()
        except Exception as exc:
            print(f"publish-event failed: {type(exc).__name__}", file=sys.stderr)
            return 1
        print("published")
        return 0
    if args.cmd == "rollback-revision":
        from privacyradar.publication import rollback_revision

        try:
            with connect() as conn:
                result = rollback_revision(
                    conn, args.revision_id, actor=args.actor, reason=args.reason
                )
                conn.commit()
        except Exception as exc:
            print(f"rollback-revision failed: {type(exc).__name__}", file=sys.stderr)
            return 1
        print(f"revision_id={result.revision_id} revision_n={result.revision_n}")
        return 0
    if args.cmd == "correction-submit":
        from privacyradar.publication import submit_correction

        try:
            with connect() as conn:
                correction_id = submit_correction(
                    conn,
                    company_id=args.company_id,
                    revision_id=args.revision_id,
                    note=args.note,
                    actor=args.actor,
                )
                conn.commit()
        except Exception as exc:
            print(f"correction-submit failed: {type(exc).__name__}", file=sys.stderr)
            return 1
        print(f"correction_id={correction_id}")
        return 0
    if args.cmd == "correction-resolve":
        from privacyradar.publication import resolve_correction

        try:
            with connect() as conn:
                replacement = resolve_correction(
                    conn,
                    args.correction_id,
                    actor=args.actor,
                    decision=args.decision,
                    note=args.note,
                )
                conn.commit()
        except Exception as exc:
            print(f"correction-resolve failed: {type(exc).__name__}", file=sys.stderr)
            return 1
        print(f"replacement_revision_id={replacement or 'none'}")
        return 0
    if args.cmd == "publish-stats":
        from privacyradar.publication import publish_stats

        try:
            with connect() as conn:
                stats = publish_stats(conn)
        except Exception as exc:
            print(f"publish-stats failed: {type(exc).__name__}", file=sys.stderr)
            return 1
        for key, value in stats.items():
            print(f"{key}={value}")
        return 0
    if args.cmd == "eval-materiality":
        from privacyradar import materiality_eval

        try:
            mat_report = materiality_eval.evaluate_materiality()
        except Exception as exc:
            print(f"eval-materiality failed: {type(exc).__name__}", file=sys.stderr)
            return 1
        print(materiality_eval.format_report(mat_report))
        if not materiality_eval.gates_pass(mat_report):
            return 1
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
