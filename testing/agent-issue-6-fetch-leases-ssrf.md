# agent-issue-6-fetch-leases-ssrf — Test Contract

Issue: https://github.com/Atharva-Kanherkar/privacyradar/issues/6
Parent epic: https://github.com/Atharva-Kanherkar/privacyradar/issues/2
Depends on: #5 (merged PR #19 at `b0b5f5d2596bd0294cc1c4997814fcfc4d98a45c`) and #4.
Base: `main` at `b0b5f5d2596bd0294cc1c4997814fcfc4d98a45c`

This contract is locked before implementation. If requirements change, update and commit this file separately before changing code.

## Outcome

Monitor catalog policy sources without duplicate work, silent gaps, or unsafe crawling. Acquisition is reliable and bounded: per-source jobs, expiring leases, retries with a documented budget, quarantine with a reason, and SSRF defenses. Semantic interpretation, publication, and notifications stay out of this issue. Tests never crawl real companies.

## Non-goals

- LLM analysis, taxonomy, extraction eval, or prompt work (#7/#8/#15).
- Publication revisions, review queues, or corrections (#8).
- Public UX redesign (#9). Catalog/API copy may mention delayed checks already from #5; do not add operator admin pages.
- Consumer auth, follows, alerts, comparisons, assistant, billing (#10–#16).
- Full operational editor UI (issue later). Operator controls in this issue are CLI + audited SQL rows.
- Production crawling of live third-party policies during tests. A single optional official public-policy smoke is N/A unless repository policy, robots, rate limits, and identifiable UA already permit it **and** the operator explicitly provides a allowlisted URL; default is fixture-server only.
- Arbitrary user-submitted URL monitoring.
- Production billing, real email, or contacting users.
- Changing observation immutability: failed fetches still never become valid snapshots.

## Invariants

1. Public claims still come only from approved publication revisions (unchanged; this issue does not publish).
2. A fetch failure is never an empty policy or a policy change. Attempts are recorded; `current_snapshot_id` does not move on failure, 304, or blocked/SSRF outcomes.
3. Observations and valid snapshots remain append-only. Concurrent workers cannot create duplicate canonical snapshots for the same `(source_id, doc_hash, normalizer_version)`.
4. Only the worker fetches external policy URLs. Web routes cannot trigger arbitrary fetches.
5. Catalog URLs are the only fetch targets. Users cannot enqueue URLs.
6. SSRF: `http`/`https` only; hostname must resolve to public unicast IPv4/IPv6; private, loopback, link-local, multicast, CGNAT (`100.64.0.0/10`), metadata (`169.254.169.254`, `fd00:ec2::254`), and IPv6 unique-local are blocked; ports limited to 80 and 443; redirects capped and re-resolved; body and time capped.
7. DNS is re-checked on every redirect hop. Connecting to a public IP then following a redirect to a private IP is blocked.
8. Robots/terms: identifiable User-Agent; robots.txt disallow → attempt `blocked` with `robots`, no body stored as a snapshot.
9. One hostile/slow domain cannot starve other domains: per-domain concurrency 1, global HTTP concurrency 8, per-request timeout.
10. Quarantined sources are not auto-claimed. Replay requires an audited operator action.
11. Model/provider routing unchanged and unused for change detection.
12. No secrets, emails, magic links, tokens, or raw exception/DSN text in logs, fixtures, CLI stderr, public APIs, or audit `reason` fields (operator `actor` is a non-email id such as `cli:local`).
13. Unknown stays unknown: a blocked or failed fetch does not prove non-collection.

## Documented budgets (locked)

| Name | Value |
|---|---|
| HTTP concurrency (global) | 8 |
| Per-registrable-domain HTTP concurrency | 1 |
| JS-render concurrency | 1 |
| Redirect hops | 3 |
| Request timeout | 30s |
| Max response body | 5 MiB |
| Allowed schemes | `http`, `https` |
| Allowed ports | 80, 443 |
| Lease TTL | 120s |
| Consecutive failures to quarantine | 5 (`HEALTH_QUARANTINE_AFTER`, already in #5) |
| Max retries per due window | 5 |
| Backoff | base 60s, factor 2, cap 6h, jitter ±20% (deterministic clock in tests) |
| Default `due_at` interval after success | 6 hours |
| User-Agent | existing identifiable `settings.crawl_user_agent` |
| Idempotency key | `fetch:{source_id}:{due_at truncated to hour UTC}` |

Retryable error codes: `timeout`, `http_5xx`, `http_429`, `network`.
Non-retryable (count as a finished attempt for the window, increment consecutive failures, do not immediately re-lease): `dns`, `tls`, `http_4xx`, `empty`, `short`, `wrong_type`, `normalize_failed`, `blocked`, `robots`, `ssrf`, `oversize`, `moved`.

`http_429` is distinct from generic `http_4xx`. `304` is success (`not_modified`): health `healthy`, consecutive_failures 0, no new observation.

## Functional Behavior

### Schema (migration `0003`)

Additive forward-only SQL. Existing `0001` and `0002` checksums must not change.

`policy_sources` additions:

- `due_at timestamptz not null default now()`
- `lease_owner text`
- `lease_token uuid`
- `lease_expires_at timestamptz`
- `retry_count integer not null default 0`
- `etag text`
- `last_modified text`
- `quarantine_reason text` (nullable; check constraint)
- `quarantined_at timestamptz`
- Index for claim: `(enabled, health_status, due_at)` where enabled and not quarantined, plus `lease_expires_at`

`quarantine_reason` allowed values: `consecutive_failures`, `invalid_content`, `blocked`, `ssrf`, `robots`, `moved`, `oversize`, `poison`.

Extended `last_failure_code` / `source_attempts.error_code` allowed values: existing #5 set plus `robots`, `ssrf`, `oversize`, `moved`, `http_429`.

New table `source_operator_actions`:

- `id uuid pk`
- `source_id uuid not null references policy_sources`
- `action text` check in (`retry`, `disable`, `enable`)
- `actor text not null` (no `@`, max 64 chars; reject values containing `@` or `://`)
- `reason text` (safe enum or short token; not a free-form email/URL dump)
- `created_at timestamptz not null default now()`
- `metadata jsonb not null default '{}'` (may include `lease_token`, `job_key`; never email/token secrets)

New table `fetch_jobs` (durable per-source work, Redis optional):

- `id uuid pk`
- `idempotency_key text not null unique`
- `source_id uuid not null references policy_sources`
- `status text` check in (`pending`, `leased`, `succeeded`, `retryable_failed`, `quarantined`, `cancelled`)
- `attempt_no integer not null default 0`
- `lease_owner text`
- `lease_token uuid`
- `lease_expires_at timestamptz`
- `run_after timestamptz not null default now()`
- `finished_at timestamptz`
- `error_code text` (same safe enum)
- `created_at timestamptz not null default now()`

Indexes: `fetch_jobs (status, run_after)`, `fetch_jobs (source_id, created_at desc)`.

`db/schema.sql` is current-head DDL including `0003` objects (no DML). CI ledger count becomes **3**. Required tables count includes `fetch_jobs` and `source_operator_actions`.

Backfill: existing sources get `due_at = now()` (or `last_success_at + interval` when last_success_at is set). No observation/snapshot rewrite.

### Scheduler and leases

Replace serial `crawl_all()` as the failure domain.

1. `schedule_due_sources(now)` selects enabled sources where `health_status <> 'quarantined'`, `enabled = true`, and (`due_at <= now` or `lease_expires_at < now` for recovery of expired leases with due work). Inserts `fetch_jobs` with the idempotency key. Duplicate key → no second row.
2. `claim_fetch_job(worker_id, now)` in one transaction: pick a due `pending`/`retryable_failed` job whose source is not leased (`lease_expires_at is null or < now`), skip sources whose registrable domain already has an unexpired lease, respect global 8. Uses `SELECT … FOR UPDATE SKIP LOCKED` on job + source rows. Sets source and job lease fields. Returns at most one job.
3. Worker fetches, then `observe_source` in its existing transaction style. Release lease. On success: `retry_count=0`, `due_at=now+6h`, job `succeeded`, store etag/last_modified if present.
4. On retryable failure: increment job `attempt_no` and source `retry_count`; if `attempt_no < 5`, set `run_after` and `due_at` from backoff, job `retryable_failed`, release lease; else treat as non-retryable finished failure for the window (consecutive_failures++, reschedule next 6h window, reset retry_count).
5. On non-retryable failure: consecutive_failures++ (already in observe); if health becomes `quarantined`, set `quarantine_reason`, job `quarantined`, do not auto-reschedule.
6. Crash between claim and finish: lease expires; another worker may reclaim. Observe uniqueness prevents duplicate snapshots. A second successful identical fetch is `deduped`.
7. `privacyradar crawl` uses the dispatcher against Postgres even when Redis is down. ARQ cron calls `schedule_due_sources` then processes claims with `max_jobs` matching the HTTP pool when Redis is configured.

Expired lease recovery does not require Redis.

### Fetch strategies

Adapter order for a claimed source:

1. `http` (conditional GET when etag/last_modified exist).
2. If HTTP 200 with HTML that classifies as `empty`/`short` (JS shell) and `playwright_fallback` is true: `js_render` once. If false: failed attempt `short`/`empty` (existing classify). Tests inject a fake render adapter; they do not require Playwright in unit tests.
3. PDF `content-type` uses the existing PDF normalizer (not a separate network strategy).

JS-render pool size 1. HTTP pool 8.

### Conditional requests and redirects

- 200: existing observe path; persist `ETag`/`Last-Modified` onto the source when present.
- 304: succeeded attempt, no new snapshot/observation, health healthy, `due_at` advanced.
- Redirects: follow ≤3; each Location must pass SSRF (scheme/port/resolve); re-check DNS; `Host` header matches the hop hostname.
- If a hop fails SSRF: attempt `blocked`/`ssrf`, no snapshot.
- If final registrable domain ≠ request registrable domain after a 301/308: still observe if SSRF-safe **and** content valid, but set last_failure_code does **not** apply on success. Record attempt `resolved_url`. If the redirect target is disallowed or empty: `moved` failure, no snapshot.
- Relative Location resolved against the previous URL.

### Robots

Before HTTP GET of the policy URL (not before SSRF classification of the URL itself): fetch/cache `robots.txt` for that origin via the same SSRF-safe client (robots.txt also must be public). If User-Agent or `*` disallows the path: do not GET the policy; attempt `blocked`/`robots`. Cache TTL 1 hour in-process (tests inject a fake robots policy). A robots fetch failure is **not** treated as allow-all and **not** treated as a policy change; it is `blocked`/`robots` (fail closed).

### Operator controls

CLI (no public HTTP):

```text
privacyradar source-retry SOURCE_ID --actor cli:local
privacyradar source-disable SOURCE_ID --actor cli:local
privacyradar source-enable SOURCE_ID --actor cli:local
```

- `retry`: insert `source_operator_actions(action=retry)`, clear `quarantine_reason`/`quarantined_at`, set `health_status` to `degraded` if a current snapshot exists else `pending`, `consecutive_failures=0`, `retry_count=0`, `due_at=now`, `enabled=true`, insert a new `fetch_jobs` row with a unique key including the action id.
- `disable`: action row, `enabled=false`, cancel pending jobs (`cancelled`), release lease.
- `enable`: action row, `enabled=true`, `due_at=now`.
- Actor validation: `^[a-z0-9][a-z0-9:_-]{1,62}$` (no `@`).
- Replaying a healthy source is allowed and audited; it does not delete observations.

### Health distinctions (user-visible remain #5 enums)

Internal `last_failure_code` distinguishes: transient (`timeout`, `http_5xx`, `http_429`, `network`), blocked (`blocked`, `robots`, `ssrf`), invalid content (`empty`, `short`, `wrong_type`, `normalize_failed`, `oversize`), moved (`moved`), plus `dns`/`tls`/`http_4xx`. Public APIs still do **not** expose raw errors or a new `last_error` field. `source_health` remains `pending|healthy|degraded|quarantined`.

### Observability

Structured logs (no PII/URLs with query strings): `source_id`, `job_id`, `attempt_id`, `outcome`, `error_code`, `lease_age_ms`, `strategy`, `http_status`. Counters (in-process + returned by dispatcher result): `jobs_scheduled`, `jobs_claimed`, `leases_expired_reclaimed`, `fetch_attempts`, `retries`, `quarantines`, `ssrf_blocked`, `robots_blocked`, `not_modified`, `domain_waits`.

`privacyradar fetch-stats` prints those counters from SQL (quarantine count, overdue count, lease age max) without URLs or emails.

### Public API / crawl surface

Unauthenticated `GET /api/health`, `/api/companies`, `/api/companies/{slug}` remain as in #5. No fetch-trigger route. `POST` to those URLs still 405/404.

## Unit Tests

- `test_ssrf_rejects_file_and_ftp_schemes`
- `test_ssrf_rejects_loopback_and_link_local_and_private_and_cgnat_and_metadata`
- `test_ssrf_rejects_non_80_443_ports`
- `test_ssrf_allows_public_https_example_via_injected_resolver`
- `test_ssrf_redirect_to_private_ip_blocked` — first hop public, Location `http://127.0.0.1/`
- `test_ssrf_dns_rebinding_second_resolve_private_blocked` — resolver returns public then private for same host
- `test_retry_backoff_monotonic_and_capped` — with frozen clock/jitter seed
- `test_retry_budget_stops_at_five`
- `test_http_429_is_retryable_http_4xx_is_not`
- `test_idempotency_key_stable_within_hour`
- `test_robots_disallow_blocks_without_fetching_body` — fake robots + fetcher call count 0 for policy URL
- `test_robots_fetch_failure_fail_closed`
- `test_conditional_304_not_modified_classification`
- `test_oversize_body_error_code`
- `test_js_shell_http_then_render_adapter_when_enabled`
- `test_actor_rejects_email_and_url`
- `test_fetch_result_does_not_put_exception_message_in_error_code`

## Integration / Functional Tests

PostgreSQL required (`pytest.mark.integration`):

- `test_migrate_fresh_includes_0003` — applied `["0001","0002","0003"]`; ledger 3; new tables exist; 0001 checksum still `5957a7874aaec1741621bfae3fff13f08fc3ca0c9222bb4592e56eac61cb3c8e`.
- `test_migrate_0002_database_upgrades_to_0003` — sources keep current_snapshot_id; due_at populated; no extra observations.
- `test_two_workers_cannot_claim_same_source` — threads; exactly one claim succeeds; the other gets none or a different source.
- `test_expired_lease_is_reclaimable` — freeze/advance clock past TTL; second worker claims.
- `test_crash_after_observe_commit_before_job_succeed_is_idempotent` — simulate: observe succeeded, job still `leased` with expired lease; reclaim + identical content → deduped, snapshots == 1.
- `test_quarantine_after_five_consecutive_nonretryable` — not claimed by scheduler.
- `test_operator_retry_creates_audit_and_enqueues` — actor `cli:local`; SQL action row; job pending; no email in row.
- `test_operator_disable_cancels_pending_jobs`
- `test_per_domain_limit` — two sources same registrable domain due; concurrent claimers get at most one leased at a time.
- `test_slow_domain_does_not_starve_other_domain` — fake fetcher sleeps on domain A; domain B completes first.
- `test_local_fixture_http_matrix` — allowlisted local server **with injected resolver mapping fixture hostname to 127.0.0.1 only inside tests** (production SSRF still rejects loopback). Matrix: 200 HTML, 304, redirect 302 to same origin, 429, 503, timeout, oversize, PDF, JS-shell HTML. Never uses catalog.yaml live URLs.
- `test_ssrf_localhost_url_blocked_without_resolver_override` — `http://127.0.0.1/` and `http://169.254.169.254/` as source.url never call the socket.
- `test_concurrent_observe_still_one_snapshot` — preserve #5 uniqueness under two claimed workers racing after both fetched identical bytes (UniqueViolation path).

Redis: `test_arq_enqueue_fetch_source_job_roundtrip` when `TEST_REDIS_URL` set; skip locally if Redis absent (CI must run).

## Smoke Tests

With migrated fixtures DB, Next running (no live crawl):

```bash
curl --fail-with-body -i http://127.0.0.1:3000/api/health
curl --fail-with-body -sS 'http://127.0.0.1:3000/api/companies?q=signal'
curl --fail-with-body -sS http://127.0.0.1:3000/api/companies/signal
```

Assert 200, Signal `source_health` enum, no `last_error`, no DSN.

Worker:

```bash
privacyradar migrate
privacyradar migrate
privacyradar fetch-stats
```

Second migrate prints `already at head`. `fetch-stats` prints integer counts, not URLs.

## E2E Tests

Playwright public smoke still passes (no login). N/A: follow, alerts, assistant, operator UI.

Optional: catalog still shows check-delayed language for degraded fixture if present; no raw `ssrf`/`ECONNREFUSED` strings in HTML.

## Manual / cURL Tests

Record sanitized commands in the PR:

1. Fresh migrate; `\d fetch_jobs`, `\d source_operator_actions`; ledger count 3.
2. Curl health/companies as above.
3. Dispatcher against FakeFetcher + real Postgres: one success, one 429 then success, one SSRF URL never snapshots.
4. Two processes claiming the same due source: one processes, one no-op.
5. `privacyradar source-retry` / `source-disable` / `source-enable` with actor `cli:local`; `select action, actor from source_operator_actions`.
6. Restart worker mentally via expired lease: set `lease_expires_at` in the past; claim succeeds.

No live Google/Apple/… fetches.

## Security / abuse

- SSRF matrix above is mandatory.
- Redirect to `file://` or `http://169.254.169.254/latest/meta-data/` blocked.
- Decompression bomb: if `Content-Encoding` would expand past 5 MiB, `oversize` (or disable transparent decompress beyond cap).
- Host header injection / DNS rebinding covered by pin-or-re-resolve tests.
- Catalog seed URLs that fail SSRF classification are rejected at seed time (do not insert) **or** inserted `enabled=false` with `quarantine_reason=ssrf` — prefer reject at seed with a safe log. Fixture URLs stay on `fixtures.privacyradar.test`.
- No fetch API on the web app.
- Log injection: error_code enum only in logs.
- Operator actor cannot be an email.

## Accessibility

N/A for new UI. Existing 320px Playwright smoke must still pass. Do not add color-only operator state on public pages.

## Performance / load

- In-process load: **100 due sources** (10× current `catalog.yaml` company count of 10) with FakeFetcher, 8 worker threads, mixed domains (at least 10 registrable domains). Assert: all jobs terminal `succeeded` or documented failure; max observed global in-flight ≤ 8; max per-domain in-flight ≤ 1; wall time budget **< 30s** locally; zero duplicate snapshots per source.
- N/A: 2,000 real HTTP connections (TEST_PLAN full-system number is #17). This issue’s 10× launch catalog is 100 fake sources.

## Failure / recovery

- DB down during claim: exception, no partial lease row committed.
- Redis down: `privacyradar crawl` still claims via Postgres; ARQ cron skipped/logged `redis_unavailable` without DSN.
- Poison job (fetch adapter raises unexpected exception): job attempt counts, after 5 → quarantine_reason `poison`; exception type name only in logs, not message.
- Observe failure after HTTP 200: existing #5 failed classification; lease released.

## Observability / rollback

- Migration 0003 additive; rollback is feature-off: stop scheduler, do not apply a down-migration. Old workers without lease columns cannot run against new schema — deploy worker with 0003 in the same release.
- `fetch-stats` and structured logs listed above.
- Feature: if `FETCH_DISPATCHER=off`, `crawl_all` may still iterate enabled non-quarantined sources **with** SSRF on each fetch (must not skip SSRF). Default on.

## Prerequisites and cleanup

- Postgres as in #4/#5. Ephemeral DBs; truncate adds `fetch_jobs`, `source_operator_actions`.
- Redis optional locally; required in CI for the ARQ test.
- Local fixture HTTP server bound to 127.0.0.1 in tests only, reached via fake DNS name + injected resolver.
- No Docker required.
- No live OpenAI. No live policy crawl in CI.
- Coverage floor remains **75%**. New modules (`ssrf`, `leases`/`jobs` dispatcher, fetch client, robots, operator CLI) need success, deny, retry, and expiry branches.

## Explicit N/A

- Payment, auth, email delivery, assistant evaluation, production DNS ownership, real 30-user study (#3).
- Official public policy URL smoke unless an allowlisted URL is already in repo policy **and** credentials/permission exist; currently they do not — skip and document.
- Admin/editor HTTP surface.
- Changing 0001/0002 SQL bytes.
