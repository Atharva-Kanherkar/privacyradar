# agent-issue-5-immutable-observations — Test Contract

Issue: https://github.com/Atharva-Kanherkar/privacyradar/issues/5
Parent epic: https://github.com/Atharva-Kanherkar/privacyradar/issues/2
Depends on: #4 (merged PR #18 at `0e9a9d168056e8fb4380d902ec4d653708a51590`)
Base: `main` at `0e9a9d168056e8fb4380d902ec4d653708a51590`

This contract is locked before implementation. If requirements change, update and commit this file separately before changing code.

## Outcome

Turn the snapshot prototype into an auditable observation system. Re-fetching an unchanged URL must not rewrite history. Every raw fetch and normalized policy version must be traceable, region-aware, and reproducible. AI must never decide whether bytes changed. A failed or blocked fetch never masquerades as an empty policy.

## Non-goals

- LLM analysis, taxonomy, extraction eval, or prompt work (issues #7/#8/#15).
- Fetch leases, bounded concurrency, SSRF hardening, retry storms, or quarantine worker behavior beyond recording source health (issue #6).
- Notification outbox, consumer auth, My Radar, comparison UI, assistant, billing (issues #10–#16).
- Catalog-page visual redesign. Catalog/status copy may change only to stop leaking raw operational errors and to show source health / freshness.
- Production crawling of live third-party policies during tests.

## Invariants

1. Observations and valid snapshots are append-only. Updates/deletes of those rows are rejected.
2. Published or public claims that exist today continue to reference snapshot IDs; new observations also have stable IDs.
3. Same raw bytes + same normalizer version → same document hash and section hashes.
4. A failed, blocked, empty, short, wrong-type, or non-2xx fetch writes a `source_attempts` row only. It does not insert a valid snapshot, does not move `current_snapshot_id`, and never uses document hash `empty` as policy truth.
5. Region variants are distinct sources (`company_id, kind, region`) and are never merged.
6. Consecutive identical successful content records an attempt and updates health, but does not duplicate snapshot bytes or create a new observation/version.
7. A → B → A creates a new observation pointing at the existing snapshot A, advances `current_snapshot_id` to A, and stores a deterministic section diff against B.
8. Source health is separate from policy truth: a degraded source still shows the last valid observation.
9. Public APIs never return raw exception strings, DSNs, stack traces, or `fetch_error` text.
10. Detection of content change is hash/section comparison only. Models are not consulted to decide whether bytes changed.

## Functional Behavior

### Schema (migration `0002`)

Additive forward-only SQL. Existing `0001` checksum must not change.

New or extended entities:

- `source_attempts`: one row per fetch attempt (started/finished, strategy, status `succeeded|failed|blocked`, HTTP metadata, resolved URL, safe `error_code`, byte count, optional snapshot/observation FKs).
- `snapshots`: immutable successful content only for new writes. Added columns: `final_url`, `language`, `region`, `strategy`, `byte_count`, `raw_sha256`, `normalized_sha256`, `normalizer_version`, `is_valid`. Unique `(source_id, doc_hash, normalizer_version)`. `fetched_at` is first-seen and is not updated on later identical fetches.
- `observations`: append-only successful content sightings. Columns include `source_id`, `snapshot_id`, `attempt_id`, `observed_at`, `region`, `previous_snapshot_id`.
- `document_changes`: deterministic section diffs when `current_snapshot_id` advances to a different snapshot (including recurrence A→B→A). No LLM fields.
- `policy_sources`: `current_snapshot_id`, `current_observation_id`, `health_status` (`pending|healthy|degraded|quarantined`), `last_attempt_at`, `last_success_at`, `last_failure_code` (safe enum, not raw errors), `consecutive_failures`.
- Indexes: `source_attempts (source_id, started_at desc)`, `observations (source_id, observed_at desc)`, `snapshots (source_id, fetched_at desc)` retained.

Triggers reject `UPDATE`/`DELETE` on `snapshots` and `observations`.

`db/schema.sql` remains the current-head reference and must include `0002` objects using idempotent DDL so docker-compose bootstrap plus `privacyradar migrate` still works.

### Fetch classification (deterministic)

A fetch is a **valid observation** only when all of:

- HTTP status is 2xx
- content-type is HTML, XHTML, plain text, markdown, or PDF
- body is non-empty and normalized text length ≥ 40 characters
- normalization succeeds

Otherwise the attempt is `failed` or `blocked` with a safe `error_code` in:

`timeout`, `dns`, `tls`, `http_4xx`, `http_5xx`, `empty`, `short`, `wrong_type`, `normalize_failed`, `network`

Raw exception messages may be logged with redaction; they are not stored on snapshots and are not returned by public APIs.

### Observe pipeline

`process_source` / `observe_source`:

1. Record a `source_attempts` row for every fetch, success or failure.
2. On invalid fetch: increment `consecutive_failures`; set health `degraded` after 1 failure, leave `quarantined` unused unless consecutive failures ≥ 5 (modeling only; issue #6 owns lease/retry policy). Do not insert a snapshot. Do not change `current_snapshot_id`.
3. On valid fetch: canonicalize with the current normalizer version; content-address by `doc_hash`.
4. If a snapshot with that `(source_id, doc_hash, normalizer_version)` exists: reuse it; do not update `fetched_at` or body columns.
5. If `current_snapshot_id` is that snapshot: record attempt as succeeded, set health `healthy`, `consecutive_failures=0`, return outcome `deduped`. No new observation.
6. If current is missing or different: insert snapshot if needed; insert observation; insert `document_changes` when previous current exists; set `current_snapshot_id` / `current_observation_id` atomically with the attempt finish.
7. LLM extract/judge runs only after a new observation exists, and never to decide the hash comparison. Existing “no API key” skip behavior remains.

Crash between statements: attempt + snapshot + observation + current pointers commit in **one transaction**. A crash leaves either the previous current snapshot or the full new observation, never a snapshot without an attempt or a moved pointer without an observation.

### Normalizer

- Version string `1.0.0` for this issue, stored on every snapshot.
- HTML/text: UTF-8 (BOM stripped), NFC, strip script/style, drop obvious cookie-banner and site-nav chrome, markdown via the existing extractor path, then `normalize_markdown`.
- PDF: extract text from bytes, then the same markdown/text normalizer.
- Replay: `normalize(raw, version=1.0.0)` is a pure function. Upgrading the version is a new code path that can re-read stored raw bytes without treating the replay as a policy change until compared under the same version.

### Backfill

On migrate to `0002` (and via `privacyradar reconcile-observations`):

- Valid existing snapshots (`fetch_error` is null, markdown length ≥ 40, `doc_hash` ≠ `empty`) gain new columns, `is_valid=true`, an observation, and `current_snapshot_id` if unset.
- Invalid existing snapshots (`fetch_error` set, empty markdown, or `doc_hash='empty'`) become `source_attempts` with safe `error_code`, `is_valid=false` if the row must be retained for FKs, and are never chosen as `current_snapshot_id`.
- CLI prints a reconciliation report: sources, valid snapshots, invalid snapshots, observations created, attempts created, current pointers set. Re-running is idempotent (counts of created rows go to zero).
- Prototype upgrade: a database with only `0001` objects and a valid snapshot row migrates to head without losing that row or its `doc_hash`.

### Public APIs and catalog status

Unauthenticated:

- `GET /api/companies` and `GET /api/companies?q=signal` → 200 JSON list. Each item includes `slug`, `name`, `source_health`, `last_verified_at` (ISO or null). No `last_error`, no exception text, no DSN.
- `GET /api/companies/{slug}` → 200 JSON for a known company including current snapshot/observation ids, region, `normalizer_version`, and recent `document_changes`. 404 for unknown slug.
- `GET /api/changes/{id}` → 200 JSON for a `document_changes` row (section add/remove/modify, snapshot ids). 404 for unknown id.
- Query `q` filters by name/slug case-insensitively. Empty `q` lists all (existing catalog size). Pagination is not required beyond a documented cap ≥ current catalog size.

Catalog HTML status column shows `healthy` / `degraded` / `pending` / `check delayed`, never raw `fetch_error`.

`GET /api/health` remains as in #4.

## Unit Tests

- `test_normalize_markdown_*` (existing) plus Unicode NFC, BOM, CRLF, blank-line collapse.
- `test_doc_hash_stable_for_same_normalizer_version` — identical input hashes; different version constant changes hash only when normalization rules change (property: 20 randomized policy-like strings).
- `test_section_hashes_*` — heading, uppercase labels, duplicate headings, empty preamble.
- `test_changed_sections_*` — add/remove/modify; identical maps → empty list.
- `test_classify_fetch_*` — 200 HTML long enough → valid; 0/timeout → `timeout`; 403/404 → `http_4xx`; 500 → `http_5xx`; `text/javascript` → `wrong_type`; empty body → `empty`; 20-char body → `short`; PDF fixture → valid text; garbage bytes → `normalize_failed`.
- `test_observe_does_not_call_model_to_compare_hashes` — FakeAnalyzer extract/judge call counts stay 0 when hashes match and when they differ if no key; hash outcome is independent of analyzer exceptions.
- `test_safe_error_code_never_contains_exception_message`.
- `test_golden_normalization_corpus` — HTML banner, nav chrome, encoding, PDF, mixed line endings. Stored expected hashes in `worker/tests/corpus/normalize/`.

## Integration / Functional Tests

PostgreSQL required (`empty_database_url` / `db_url`):

- Fresh migrate applies `["0001","0002"]`. Re-migrate applies `[]`. Ledger count is 2. Required new tables exist.
- `0001`-only database with a valid snapshot and an invalid empty/`fetch_error` snapshot upgrades: valid row kept, observation created, current pointer set, invalid row not current, attempts created, reconcile report matches counts. Second reconcile creates 0 new observations.
- Triggers: `UPDATE snapshots SET markdown='x'` raises; `DELETE FROM observations` raises.
- Unique `(source_id, doc_hash, normalizer_version)` rejects a second insert.
- `observe_source` success persists attempt + snapshot + observation + healthy source in one transaction.
- Repeat identical fetch: attempt count +1, snapshot count unchanged, observation count unchanged, `fetched_at` unchanged.
- Content change: new snapshot, new observation, `document_changes` with expected section names, current pointer advances.
- A→B→A: three successful fetches, two snapshot rows (A and B), three attempts, observations for each version change (A, B, A again), final `current_snapshot_id` is A’s id, last diff is B→A.
- Failed fetch after a valid observation: attempt failed, snapshot/observation counts unchanged, `current_snapshot_id` unchanged, health `degraded`, public API still returns last verified snapshot id.
- Concurrent two workers inserting the same new hash: one snapshot row, two attempts, at most one new observation for that hash while current already matches (or exactly one observation if current was empty). No exception leak.
- Partial failure: if observation insert fails, snapshot insert rolls back (or unused snapshot is not current). Use a failing trigger or constraint in the test database.
- Region: two sources (global vs EU) with identical bytes produce two snapshots/observations; they are not merged.
- Metrics: after a mixed run, tests can read attempt / new-version / dedupe / normalize-failure counts from the observe result and/or SQL.

## Smoke Tests

With local Postgres, migrated + `seed-fixtures`, Next running:

```bash
curl --fail-with-body -i http://127.0.0.1:3000/api/health
curl --fail-with-body -sS 'http://127.0.0.1:3000/api/companies?q=signal'
curl --fail-with-body -sS http://127.0.0.1:3000/api/companies/signal
```

Assert:

- health 200 `status=ok`.
- companies search 200, JSON array, Signal present, `source_health` is a known enum, no `last_error` key, body does not contain `postgresql://` or exception class names from fetch failures.
- company detail 200, `current_snapshot_id` UUID, `region` present.
- `GET /api/companies/does-not-exist` → 404.
- `GET /api/changes/00000000-0000-0000-0000-000000000000` → 404.

Worker:

```bash
privacyradar migrate
privacyradar reconcile-observations
```

Second reconcile is idempotent. Stderr on DB failure does not print the DSN (same CLI rule as #4).

## E2E Tests

Playwright public smoke still passes. Add assertions:

- Catalog status for Signal is not a raw timeout/DNS string; it is a health/freshness word.
- Company page still renders Signal without login.
- Optional: request `/api/companies?q=signal` from Playwright `request` and assert schema as in smoke.

N/A: auth, follow, alerts, assistant journeys.

## Manual / cURL Tests

Record sanitized commands in the PR:

1. Migrate fresh DB; `\d source_attempts`, `\d observations`, `\d document_changes`.
2. Seed fixtures; curl companies APIs as above.
3. Run `observe_source` twice with FakeFetcher identical HTML against real Postgres; SQL counts as in integration tests.
4. Inject timeout FakeFetcher; confirm last valid snapshot remains current; curl company JSON `source_health=degraded` or equivalent and `last_verified_at` still set.
5. Restart web process; curl still returns the same snapshot id (durable).

## Security / abuse

- Public company/change APIs are read-only. POST/PUT/PATCH/DELETE return 405 or 404.
- SQL injection: slug and `q` parameterized; `q` with `' OR 1=1` does not dump all extra tables or error text.
- XSS: JSON responses are JSON, not HTML. Catalog does not render `fetch_error`.
- No secrets, emails, or magic links in new fixtures/logs.
- Raw HTML is not executed. Public APIs do not return full `raw_html`.

## Accessibility

- Catalog status text remains visible text (not color-only).
- Existing 320px smoke still passes.
- N/A: new interactive widgets.

## Performance

- Company list query does not select `raw_html` or full markdown.
- Indexes exist as named above. No load test beyond 50 sequential observes in one integration test (budget: < 5s locally).

## Failure / recovery

- DB down: health 503 as in #4; company API 503 with `{"error":"unavailable"}` and no DSN (do not return empty catalog as success).
- Invalid UUID in `/api/changes/{id}` → 404, not 500.
- Normalization failure increments normalize-failure metric and writes failed attempt.

## Observability

Structured log fields (no PII): `source_id`, `attempt_id`, `snapshot_id`, `outcome` (`deduped|new_version|failed`), `error_code`, `normalizer_version`.

## Prerequisites and cleanup

- Postgres as in #4 (`TEST_ADMIN_DATABASE_URL` / local Homebrew).
- Ephemeral databases from `conftest.py`; truncate includes new tables.
- No Docker required.
- No live OpenAI. No live policy crawl in CI.
- Coverage floor remains **75%**. New modules (`observe`, `normalize` extras, `classify`, APIs) need success/failure/dedupe branches covered.

## Explicit N/A

- Payment, auth, email, assistant evaluation, production DNS, real 30-user study.
- Full SSRF matrix (issue #6) except: catalog fixture URLs stay on `fixtures.privacyradar.test` and tests do not fetch link-local addresses.
