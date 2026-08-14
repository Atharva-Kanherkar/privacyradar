from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, wait
from datetime import UTC, datetime, timedelta
from threading import Barrier, Lock
from time import monotonic, sleep

import psycopg
import pytest
from psycopg.rows import dict_row

from privacyradar.crawl import FetchResult
from privacyradar.leases import (
    ClaimedJob,
    claim_fetch_job,
    drain_once,
    fetch_stats,
    run_claimed_job,
    schedule_due_sources,
)
from privacyradar.operator import source_disable, source_retry
from privacyradar.retry import LEASE_SECONDS
from privacyradar.ssrf import registrable_domain
from privacyradar.testing.fixtures import make_company, make_source
from privacyradar.testing.persist import persist_company, persist_source

pytestmark = pytest.mark.integration

POLICY = "# Privacy\nWe collect your email address to create an account.\n"


def _connect(url: str) -> psycopg.Connection[dict[str, object]]:
    return psycopg.connect(url, row_factory=dict_row)


def _fetch(
    url: str, markdown: str = POLICY, *, error: str | None = None, status: int = 200,
    etag: str | None = None, last_modified: str | None = None,
) -> FetchResult:
    return FetchResult(
        url=url,
        status=status if error is None else 0,
        content_type="text/html",
        html=f"<article>{markdown}</article>",
        markdown="" if error else markdown,
        error=error,
        body=(markdown.encode() if error is None else b""),
        etag=etag,
        last_modified=last_modified,
    )


def _seed(
    url: str,
    slug: str,
    *,
    source_url: str | None = None,
    clock: datetime | None = None,
) -> dict[str, object]:
    company = make_company(slug=slug)
    source = make_source(company, url=source_url or f"https://{slug}.example.test/privacy")
    due = clock or datetime.now(UTC)
    with _connect(url) as conn:
        persist_company(conn, company)
        persist_source(conn, source)
        conn.execute(
            "update policy_sources set due_at = %s, enabled = true where id = %s",
            (due, str(source.id)),
        )
        conn.commit()
    return {
        "source_id": str(source.id),
        "company_id": str(company.id),
        "slug": company.slug,
        "url": source.url,
    }


def test_two_workers_cannot_claim_same_source(db_url: str) -> None:
    clock = datetime.now(UTC)
    source = _seed(db_url, "lease-race", clock=clock)

    def worker(name: str) -> str | None:
        with _connect(db_url) as conn:
            schedule_due_sources(conn, clock)
            claimed = claim_fetch_job(conn, name, clock)
            conn.commit()
            return None if claimed is None else claimed.source["source_id"]

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(worker, ["w1", "w2"]))
    claimed = [item for item in results if item is not None]
    assert claimed == [source["source_id"]]


def test_expired_lease_is_reclaimable(db_url: str) -> None:
    start = datetime.now(UTC)
    _seed(db_url, "lease-expire", clock=start)
    with _connect(db_url) as conn:
        schedule_due_sources(conn, start)
        first = claim_fetch_job(conn, "w1", start)
        conn.commit()
        assert first is not None
        later = start + timedelta(seconds=LEASE_SECONDS + 1)
        second = claim_fetch_job(conn, "w2", later)
        conn.commit()
    assert second is not None
    assert second.job_id == first.job_id
    assert second.lease_token != first.lease_token


def test_quarantine_after_five_consecutive_nonretryable(db_url: str) -> None:
    clock = datetime.now(UTC)
    source = _seed(db_url, "poison-src", clock=clock)

    def fail(_url: str) -> FetchResult:
        return _fetch(_url, error="ssrf")

    with _connect(db_url) as conn:
        for index in range(5):
            conn.execute(
                "update policy_sources set due_at = %s, health_status = 'degraded' where id = %s",
                (clock + timedelta(hours=index), source["source_id"]),
            )
            drain_once(conn, worker_id=f"w{index}", fetch=fail, now=clock + timedelta(hours=index))
        conn.commit()
        row = conn.execute(
            "select health_status, quarantine_reason from policy_sources where id = %s",
            (source["source_id"],),
        ).fetchone()
        scheduled = schedule_due_sources(conn, clock + timedelta(days=1))
        conn.commit()
    assert row is not None
    assert row["health_status"] == "quarantined"
    assert row["quarantine_reason"] == "ssrf"
    assert scheduled == 0


def test_operator_retry_creates_audit_and_enqueues(db_url: str) -> None:
    clock = datetime.now(UTC)
    source = _seed(db_url, "retry-src", clock=clock)
    with _connect(db_url) as conn:
        conn.execute(
            """
            update policy_sources
            set health_status = 'quarantined',
                quarantine_reason = 'ssrf',
                consecutive_failures = 5
            where id = %s
            """,
            (source["source_id"],),
        )
        action_id = source_retry(conn, str(source["source_id"]), actor="cli:local", now=clock)
        conn.commit()
        action = conn.execute(
            "select action, actor, reason, metadata from source_operator_actions"
        ).fetchone()
        jobs = conn.execute(
            "select status, idempotency_key from fetch_jobs"
        ).fetchall()
        src = conn.execute(
            "select health_status, quarantine_reason, enabled from policy_sources"
        ).fetchone()
    assert action is not None
    assert action["action"] == "retry"
    assert action["actor"] == "cli:local"
    assert "@" not in action["actor"]
    assert "retry:" in str(action["metadata"])
    assert any(row["status"] == "pending" for row in jobs)
    assert src is not None
    assert src["enabled"] is True
    assert src["quarantine_reason"] is None
    assert src["health_status"] == "pending"
    assert action_id


def test_operator_disable_cancels_pending_jobs(db_url: str) -> None:
    clock = datetime.now(UTC)
    source = _seed(db_url, "disable-src", clock=clock)
    with _connect(db_url) as conn:
        schedule_due_sources(conn, clock)
        source_disable(conn, str(source["source_id"]), actor="cli:local")
        conn.commit()
        jobs = conn.execute("select status from fetch_jobs").fetchall()
        src = conn.execute("select enabled from policy_sources").fetchone()
    assert src is not None and src["enabled"] is False
    assert all(row["status"] == "cancelled" for row in jobs)
    from privacyradar.operator import source_enable

    with _connect(db_url) as conn:
        source_enable(conn, str(source["source_id"]), actor="cli:local")
        conn.commit()
        enabled = conn.execute("select enabled from policy_sources").fetchone()
    assert enabled is not None and enabled["enabled"] is True


def test_per_domain_limit(db_url: str) -> None:
    clock = datetime.now(UTC)
    _seed(
        db_url, "dom-a", source_url="https://same.example.test/one", clock=clock
    )
    _seed(db_url, "dom-b", source_url="https://same.example.test/two", clock=clock)
    with _connect(db_url) as conn:
        schedule_due_sources(conn, clock)
        one = claim_fetch_job(conn, "w1", clock)
        two = claim_fetch_job(conn, "w2", clock)
        conn.commit()
    assert one is not None
    assert two is None


def test_per_domain_limit_under_concurrent_claimers(db_url: str) -> None:
    clock = datetime.now(UTC)
    _seed(db_url, "cdom-a", source_url="https://same.example.test/one", clock=clock)
    _seed(db_url, "cdom-b", source_url="https://same.example.test/two", clock=clock)

    def worker(name: str) -> str | None:
        with _connect(db_url) as conn:
            schedule_due_sources(conn, clock)
            claimed = claim_fetch_job(conn, name, clock)
            conn.commit()
            return None if claimed is None else str(claimed.source["source_id"])

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(worker, ["w1", "w2"]))
    claimed = [item for item in results if item is not None]
    assert len(claimed) == 1


def test_slow_domain_does_not_starve_other_domain(db_url: str) -> None:
    clock = datetime.now(UTC)
    _seed(db_url, "slowco", source_url="https://slow.test/p", clock=clock)
    _seed(db_url, "fastco", source_url="https://fast.test/p", clock=clock)
    order: list[str] = []
    lock = Lock()
    claimed_ready = Barrier(2, timeout=5)

    def fetch(url: str) -> FetchResult:
        if "slow.test" in url:
            sleep(0.4)
        with lock:
            order.append(url)
        return _fetch(url)

    started = monotonic()
    with _connect(db_url) as conn:
        schedule_due_sources(conn, clock)
        conn.commit()

    def worker(name: str) -> str:
        with _connect(db_url) as conn:
            claimed = claim_fetch_job(conn, name, clock)
            conn.commit()
            claimed_ready.wait()
            assert claimed is not None
            message = run_claimed_job(conn, claimed, fetch=fetch, now=clock)
            conn.commit()
            return message

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(worker, "wa"), pool.submit(worker, "wb")]
        wait(futures)
        done = [fut.result() for fut in futures]
    elapsed = monotonic() - started
    assert len(done) == 2
    assert len(order) == 2
    assert "fast.test" in order[0]
    assert "slow.test" in order[1]
    assert elapsed < 1.0


def test_crash_after_observe_commit_before_job_succeed_is_idempotent(db_url: str) -> None:
    clock = datetime.now(UTC)
    source = _seed(db_url, "crash-src", clock=clock)
    with _connect(db_url) as conn:
        from privacyradar.observe import observe_source

        payload = {
            **source,
            "name": "Crash",
            "region": "global",
            "company_id": source["company_id"],
        }
        observe_source(conn, payload, _fetch(str(source["url"])))
        schedule_due_sources(conn, clock)
        claimed = claim_fetch_job(conn, "w1", clock)
        conn.commit()
        assert claimed is not None
        conn.execute(
            "update fetch_jobs set lease_expires_at = %s where id = %s",
            (clock - timedelta(seconds=1), claimed.job_id),
        )
        conn.execute(
            "update policy_sources set lease_expires_at = %s where id = %s",
            (clock - timedelta(seconds=1), source["source_id"]),
        )
        conn.commit()
        later = clock + timedelta(seconds=1)
        reclaimed = claim_fetch_job(conn, "w2", later)
        assert reclaimed is not None
        from privacyradar.leases import run_claimed_job

        message = run_claimed_job(conn, reclaimed, fetch=lambda url: _fetch(url), now=later)
        conn.commit()
        snaps = conn.execute("select count(*) as n from snapshots").fetchone()
    assert snaps is not None and snaps["n"] == 1
    assert "unchanged" in message


def test_fetch_stats_has_integer_counts(db_url: str) -> None:
    clock = datetime.now(UTC)
    _seed(db_url, "stats-src", clock=clock)
    with _connect(db_url) as conn:
        stats = fetch_stats(conn, clock)
    assert set(stats) == {
        "overdue_sources",
        "quarantined_sources",
        "active_leases",
        "pending_jobs",
    }
    assert all(isinstance(value, int) for value in stats.values())
    assert "http://" not in str(stats)


def test_load_100_due_sources_respects_pools(db_url: str) -> None:
    clock = datetime.now(UTC)
    inflight = 0
    max_inflight = 0
    per_domain: dict[str, int] = {}
    max_domain = 0
    lock = Lock()

    for index in range(100):
        domain_i = index % 10
        _seed(
            db_url,
            f"load{index}",
            source_url=f"https://s{index}.example{domain_i}.test/privacy",
            clock=clock,
        )

    def fetch(url: str) -> FetchResult:
        nonlocal inflight, max_inflight, max_domain
        host = url.split("/")[2]
        domain = registrable_domain(host)
        with lock:
            inflight += 1
            max_inflight = max(max_inflight, inflight)
            per_domain[domain] = per_domain.get(domain, 0) + 1
            max_domain = max(max_domain, per_domain[domain])
        try:
            return _fetch(url)
        finally:
            with lock:
                inflight -= 1
                per_domain[domain] -= 1

    started = monotonic()
    with _connect(db_url) as conn:
        schedule_due_sources(conn, clock)
        conn.commit()

    def worker(name: str) -> int:
        count = 0
        with _connect(db_url) as conn:
            while True:
                claimed = claim_fetch_job(conn, name, clock)
                if claimed is None:
                    conn.commit()
                    break
                conn.commit()
                run_claimed_job(conn, claimed, fetch=fetch, now=clock)
                conn.commit()
                count += 1
        return count

    with ThreadPoolExecutor(max_workers=8) as pool:
        finished = list(pool.map(worker, [f"w{i}" for i in range(8)]))
    elapsed = monotonic() - started
    with _connect(db_url) as conn:
        jobs = conn.execute("select status from fetch_jobs").fetchall()
        snaps = conn.execute(
            "select source_id, count(*) as n from snapshots group by source_id"
        ).fetchall()
    assert sum(finished) == 100
    assert elapsed < 30
    assert all(row["status"] == "succeeded" for row in jobs)
    assert all(row["n"] == 1 for row in snaps)
    assert max_inflight <= 8
    assert max_domain <= 1


def test_retryable_failures_do_not_quarantine_until_budget_exhausted(db_url: str) -> None:
    clock = datetime.now(UTC)
    source = _seed(db_url, "retry-budget", clock=clock)

    def limited(_url: str) -> FetchResult:
        return _fetch(_url, error="http_429")

    with _connect(db_url) as conn:
        schedule_due_sources(conn, clock)
        conn.commit()
        for index in range(4):
            now = clock + timedelta(seconds=index * 90)
            conn.execute(
                "update fetch_jobs set run_after = %s where source_id = %s",
                (now, source["source_id"]),
            )
            conn.commit()
            claimed = claim_fetch_job(conn, f"r{index}", now)
            assert claimed is not None
            run_claimed_job(conn, claimed, fetch=limited, now=now)
            conn.commit()
        row = conn.execute(
            """
            select health_status, consecutive_failures, quarantine_reason
            from policy_sources where id = %s
            """,
            (source["source_id"],),
        ).fetchone()
        attempts = conn.execute(
            "select count(*) as n from source_attempts where source_id = %s",
            (source["source_id"],),
        ).fetchone()
    assert row is not None
    assert attempts is not None and attempts["n"] == 4
    assert row["consecutive_failures"] == 0
    assert row["health_status"] != "quarantined"
    assert row["quarantine_reason"] is None

    with _connect(db_url) as conn:
        now = clock + timedelta(seconds=8 * 90)
        conn.execute(
            "update fetch_jobs set run_after = %s where source_id = %s",
            (now, source["source_id"]),
        )
        conn.commit()
        claimed = claim_fetch_job(conn, "r4", now)
        assert claimed is not None
        run_claimed_job(conn, claimed, fetch=limited, now=now)
        conn.commit()
        row = conn.execute(
            """
            select health_status, consecutive_failures, quarantine_reason
            from policy_sources where id = %s
            """,
            (source["source_id"],),
        ).fetchone()
    assert row is not None
    assert row["consecutive_failures"] == 1
    assert row["health_status"] == "degraded"
    assert row["quarantine_reason"] is None


def test_dispatcher_sends_conditional_get_headers(db_url: str) -> None:
    clock = datetime.now(UTC)
    source = _seed(db_url, "etag-src", clock=clock)
    seen: list[str | None] = []

    def fetch(
        url: str, etag: str | None = None, last_modified: str | None = None
    ) -> FetchResult:
        seen.append(etag)
        if etag == '"v1"':
            return FetchResult(
                url=url,
                status=304,
                content_type="text/html",
                html="",
                markdown="",
                body=b"",
                etag=etag,
                last_modified=last_modified,
            )
        return _fetch(url, etag='"v1"', last_modified="Wed, 01 Jan 2025 00:00:00 GMT")

    with _connect(db_url) as conn:
        drain_once(conn, worker_id="w1", fetch=fetch, now=clock)
        later = clock + timedelta(hours=7)
        conn.execute(
            "update policy_sources set due_at = %s where id = %s",
            (later, source["source_id"]),
        )
        drain_once(conn, worker_id="w2", fetch=fetch, now=later)
        snaps = conn.execute("select count(*) as n from snapshots").fetchone()
    assert seen[0] is None
    assert '"v1"' in seen[1:]
    assert snaps is not None and snaps["n"] == 1


def test_poison_job_records_attempts_then_quarantines(db_url: str) -> None:
    clock = datetime.now(UTC)
    source = _seed(db_url, "poison-job", clock=clock)

    def boom(_url: str) -> FetchResult:
        raise RuntimeError("secret details")

    messages: list[str] = []
    with _connect(db_url) as conn:
        schedule_due_sources(conn, clock)
        conn.commit()
        for index in range(5):
            now = clock + timedelta(minutes=index * 5)
            conn.execute(
                "update fetch_jobs set run_after = %s where source_id = %s",
                (now, source["source_id"]),
            )
            conn.commit()
            claimed = claim_fetch_job(conn, f"p{index}", now)
            assert claimed is not None
            messages.append(run_claimed_job(conn, claimed, fetch=boom, now=now))
            conn.commit()
        row = conn.execute(
            """
            select health_status, quarantine_reason from policy_sources where id = %s
            """,
            (source["source_id"],),
        ).fetchone()
        attempts = conn.execute(
            "select error_code from source_attempts where source_id = %s",
            (source["source_id"],),
        ).fetchall()
    assert row is not None
    assert row["health_status"] == "quarantined"
    assert row["quarantine_reason"] == "poison"
    assert len(attempts) == 5
    assert all(item["error_code"] == "network" for item in attempts)
    assert all("secret" not in message for message in messages)


def test_concurrent_claimed_workers_still_one_snapshot(db_url: str) -> None:
    clock = datetime.now(UTC)
    source = _seed(db_url, "race-src", clock=clock)
    with _connect(db_url) as conn:
        schedule_due_sources(conn, clock)
        first = claim_fetch_job(conn, "w1", clock)
        assert first is not None
        conn.execute(
            "update fetch_jobs set lease_expires_at = %s where id = %s",
            (clock - timedelta(seconds=1), first.job_id),
        )
        conn.execute(
            "update policy_sources set lease_expires_at = %s where id = %s",
            (clock - timedelta(seconds=1), source["source_id"]),
        )
        conn.commit()
        later = clock + timedelta(seconds=1)
        second = claim_fetch_job(conn, "w2", later)
        assert second is not None
        conn.commit()

    def run(claimed: ClaimedJob) -> str:
        with _connect(db_url) as conn:
            message = run_claimed_job(
                conn, claimed, fetch=lambda url: _fetch(url), now=later
            )
            conn.commit()
            return message

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(run, [first, second]))
    with _connect(db_url) as conn:
        snaps = conn.execute("select count(*) as n from snapshots").fetchone()
    assert snaps is not None and snaps["n"] == 1


def test_source_enable_rejects_quarantined_source(db_url: str) -> None:
    from privacyradar.operator import OperatorError, source_enable

    clock = datetime.now(UTC)
    source = _seed(db_url, "enable-q", clock=clock)
    with _connect(db_url) as conn:
        conn.execute(
            """
            update policy_sources
            set health_status = 'quarantined', quarantine_reason = 'ssrf'
            where id = %s
            """,
            (source["source_id"],),
        )
        conn.commit()
        with pytest.raises(OperatorError, match="source-retry"):
            source_enable(conn, str(source["source_id"]), actor="cli:local")

