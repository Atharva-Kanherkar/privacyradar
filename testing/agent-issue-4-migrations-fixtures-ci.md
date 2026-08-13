# agent-issue-4-migrations-fixtures-ci — Test Contract

Issue: https://github.com/Atharva-Kanherkar/privacyradar/issues/4
Parent epic: https://github.com/Atharva-Kanherkar/privacyradar/issues/2
Base: `main` at merge SHA `22739d2a969d5cd923a23d0ab11995d110529051` (PR #1)

This contract is locked before implementation. If requirements change, update and commit this file separately before changing code.

## Outcome

Create a safe engineering floor: numbered forward-only SQL migrations with a ledger, deterministic fixture factories, ephemeral PostgreSQL/Redis integration tests, a browser-smoke harness, and documented required CI/branch-protection checks. Preserve the public site and current worker CLI. Do not introduce auth or consumer product features.

## Baseline (measured on `22739d2`, 2026-08-13)

| Gate | Result |
|---|---|
| Worker ruff/mypy | pass |
| Worker pytest | 13 passed in 5.61s |
| Worker coverage | 54.66% statements (`--cov-fail-under=45`) |
| Web lint / `tsc --noEmit` / build | pass; compile ~884ms |
| `db/schema.sql` apply + reapply on empty Postgres | 5 required tables; `CREATE IF NOT EXISTS` notices; no error |
| Main CI | success, run `31733208765` |
| Branch protection | required checks: Web lint/typecheck/build; Worker lint/typecheck/test; PostgreSQL schema validation; Dependency review. `strict: true`, linear history, conversation resolution, enforce_admins |
| Local Docker daemon | unavailable |
| Local Postgres | Homebrew 17.9 on `:5432` |
| Local Redis | not installed |

Coverage floor for this PR: **must not go below 54%**. New modules (`migrate`, fixtures, fakes, CLI migrate/seed-fixtures, health route) require meaningful branch coverage of success, duplicate, and failure paths.

## Functional Behavior

### Migrations

- Migration files live at `db/migrations/NNNN_name.sql` with `NNNN` a 4-digit integer. Ordering is numeric, then filename.
- A Python runner (`privacyradar migrate`) is the only supported apply path for applications and CI.
- On a **fresh** database: runner creates ledger `schema_migrations(version, name, checksum, applied_at)` if missing, takes a Postgres advisory lock, applies each pending file in one transaction per file, records checksum (SHA-256 of file bytes), and reaches head.
- Applying migrations **twice** is a no-op: already-recorded versions are skipped; objects already created by `0001` remain; no duplicate ledger rows; exit 0.
- If an applied version’s file checksum **differs** from the ledger, migrate **aborts** before applying later files. No partial rewrite of the mismatched version.
- A failed statement inside a migration file rolls back **that file only**. Previously recorded versions remain. Ledger has no row for the failed version.
- **Prototype upgrade**: a database that already has the PR #1 tables (`companies`, `policy_sources`, `snapshots`, `extractions`, `change_events`) and production-shaped rows, but no ledger, must migrate to head **without dropping or rewriting** those rows. After upgrade, ledger records `0001` and row counts/ids match the pre-upgrade snapshot.
- `db/schema.sql` remains a current-head reference. It must match the concatenation of applied numbered SQL (except the runner-managed ledger table).
- No down-migrations. Recovery is additive forward migrations plus feature-off, not destructive rollback of schema.
- Concurrent migrate processes serialize on the advisory lock; the second waiter applies zero additional files after the first completes.

### Fixtures

- Factories exist for: company, source, observation (snapshot-shaped), claim (extraction-shaped), user, follow, notification.
- IDs are stable for the same logical key (UUID5 from a fixed namespace + entity key). Timestamps use a frozen clock default (`2026-01-15T12:00:00Z`) unless a test clock is injected.
- Factories **must not** call live HTTP, OpenAI, email, or other network APIs. Import graph of the fixture module must not invoke `httpx`/`openai` clients at import or build time.
- Isolation: persisting fixtures in test A cannot be visible to test B after teardown (truncate or dedicated database). Two factories with different keys produce different IDs; the same key reproduces the same ID.
- Users/follows/notifications may be in-memory records until those tables exist. Persist helpers for current tables (company, source, observation/snapshot, claim/extraction) write explicit ids/timestamps.
- Fixture emails, if any, use `@example.test` or similarly reserved names. No real addresses, tokens, or magic links appear in fixtures, logs, or assertions.

### Integration harness

- Worker integration tests run against a real PostgreSQL instance (CI service container; locally an ephemeral database on the available server).
- Redis tests run against a real Redis 7 when `TEST_REDIS_URL` or a CI Redis service is present; if Redis is absent locally and `CI` is unset, those tests skip with an explicit reason. In CI they must run and pass.
- A worker job/pipeline integration test processes a source using **fake** network and model adapters, persists a snapshot through real Postgres, and never opens a live policy URL or model provider.
- Fake adapters can inject success, timeout, empty body, and invalid model output without touching the network.

### Health and public smoke

- `GET /api/health` returns JSON. Process up + DB connected → `200` with `{"status":"ok","database":"connected"}`. Process up + `DATABASE_URL` set + DB down → `503` with `{"status":"degraded","database":"unavailable"}`. No connection strings, secrets, or emails in the body.
- Browser smoke (Playwright, Chromium): unauthenticated visit to `/`, `/companies`, `/companies/{seeded-slug}`, `/about`, `/feed.xml`, `/api/health`. Assert 200 (feed may be 200 XML), visible `h1`, nav to Companies/About, seeded company name visible, health JSON `status=ok`.
- Public browsing requires no authentication.

### CI and branch protection

- CI remains concurrency-cancelled, `permissions.contents: read`, time-bounded, `pull_request` + `push` to `main` (never `pull_request_target`).
- Jobs (names are the GitHub check titles):
  1. `Web lint, typecheck, build`
  2. `Worker lint, typecheck, test` (includes unit + integration against service Postgres/Redis)
  3. `PostgreSQL schema validation` (fresh migrate, re-migrate, prototype-upgrade migrate, required tables + ledger)
  4. `Dependency review` (pull_request only; fail-on-severity moderate)
  5. `Browser smoke`
  6. `PR secret guard` (pull_request): workflow files do not use `pull_request_target` and do not interpolate deployment `secrets.*` into PR jobs
- Coverage cannot be lowered below 54% without an explicit contract amendment.
- Branch-protection **setup is documented for an owner**. This PR must not admin-bypass protection. New check names are listed so an owner can add them after they exist on `main`. Until then, currently required checks still gate merge.
- A failed required check prevents merge (already true for the four existing checks).

### Non-goals / invariants

- No magic-link auth, watchlists, notifications product UI, billing, assistant, or catalog expansion.
- Do not crawl live policy URLs in tests.
- Do not weaken or skip existing tests.
- Fetch failure is still never an empty successful policy (pipeline behavior unchanged except through fakes in tests).
- Public claims still come only from existing publication tables; this issue does not add a publication workflow.
- Worker CLI `seed`, `crawl`, and `extract` keep working. New subcommands: `migrate`, `seed-fixtures`.

## Unit Tests

- `test_parse_migrations_orders_numeric_versions` — `0002` sorts after `0001`; ignores non-matching files.
- `test_migration_checksum_is_sha256_of_bytes` — checksum changes when SQL bytes change.
- `test_fixture_ids_are_stable_and_unique_per_key` — same slug → same UUID; different slug → different UUID.
- `test_fixture_clock_is_frozen_by_default` — `created_at`/`fetched_at` equal frozen timestamp.
- `test_fixture_module_does_not_import_live_clients` — `privacyradar.testing.fixtures` import graph excludes `httpx` and `openai`.
- `test_fake_fetcher_returns_configured_results_and_errors` — success, timeout, empty markdown.
- `test_fake_analyzer_returns_configured_practices_and_judgement` — no OpenAI client constructed.
- `test_cli_migrate_help_and_unknown_command` — `privacyradar migrate --help` exits 0; unknown cmd exits non-zero.
- `test_health_payload_shape_unit` — N/A as a Python unit test; covered by the web route via Playwright and `curl`. If a small TypeScript test runner is added, assert JSON shape; otherwise document as smoke/curl only.

## Integration / Functional Tests

- `test_migrate_fresh_database_to_head` — empty DB → ledger + 5 domain tables + `schema_migrations` row for `0001`.
- `test_migrate_is_idempotent` — apply twice; table counts and ledger row count unchanged; second apply reports already at head.
- `test_migrate_rejects_checksum_mismatch` — tamper ledger checksum; migrate raises; domain data untouched.
- `test_migrate_failed_file_does_not_record_version` — inject a bad SQL file in a temp migrations dir; version absent from ledger; no leftover objects from that file.
- `test_migrate_upgrades_prototype_schema_preserving_rows` — load current `schema.sql` (or equivalent CREATE IF NOT EXISTS prototype), insert a company/source/snapshot with known ids, run migrate, assert ids and `doc_hash` survive and ledger contains `0001`.
- `test_fixture_persistence_round_trip` — persist company+source+observation+claim; SELECT matches; truncate/isolation fixture hides them from the next test.
- `test_fixture_isolation_between_tests` — implemented as two tests that each insert a uniquely keyed company and assert the other key is absent.
- `test_process_source_with_fakes_persists_snapshot` — fake 200 HTML/markdown; real DB; `snapshots` row with expected `doc_hash`; no extraction when model key absent / fake analyzer unused on first snapshot without key.
- `test_process_source_fetch_failure_does_not_look_like_empty_success` — fake timeout; snapshot has `fetch_error`; `doc_hash` is not treated as a successful empty policy by the returned status string (`fetch failed`).
- `test_redis_ping_when_configured` — `PING` → `PONG` against CI/local Redis.

## Smoke Tests

```bash
# Worker
cd worker
python -m pip install -e '.[dev]'
ruff check privacyradar tests
mypy privacyradar
pytest

# Web
cd web
npm ci
npm run lint
npx tsc --noEmit
npm run build

# Health (app + migrated DB running)
curl --fail-with-body -i http://127.0.0.1:3000/api/health
# expect: HTTP/1.1 200, JSON status=ok, database=connected
```

## E2E Tests

Playwright Chromium, seeded fixture company `signal` (or the factory default slug):

1. `/` — 200, heading “What they take. What just changed.”, nav links Companies and About.
2. `/companies` — 200, table or list includes seeded company name.
3. `/companies/{slug}` — 200, `h1` is the company name, link to privacy policy present.
4. `/about` — 200, `h1` About.
5. `/feed.xml` — 200, `content-type` includes `xml`.
6. Unauthenticated throughout (no login UI required).

Viewport: default desktop. Mobile 320px is **not** a merge blocker for this foundation issue; note as follow-up if not included. Prefer including a 320px home-page heading visibility check if cheap.

## Manual / cURL Tests

Prerequisites: migrated local DB, `privacyradar seed-fixtures`, `cd web && npm run build && npm run start -- --port 3000` with `DATABASE_URL` set. No secrets printed.

```bash
curl --fail-with-body -sS -o /tmp/pr-health.json -w '%{http_code}' http://127.0.0.1:3000/api/health
# expect 200 and $(jq -r .status /tmp/pr-health.json)=ok

curl --fail-with-body -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:3000/
# expect 200

curl --fail-with-body -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:3000/companies
# expect 200

curl --fail-with-body -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:3000/companies/signal
# expect 200 if seed-fixtures used default signal slug

curl --fail-with-body -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:3000/about
# expect 200

curl --fail-with-body -sS -D - -o /tmp/pr-feed.xml http://127.0.0.1:3000/feed.xml | head
# expect 200 and XML

curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:3000/companies/this-slug-does-not-exist
# expect 404
```

Assert response bodies do not contain `DATABASE_URL`, `OPENAI`, `postgresql://`, or `@gmail.`.

## Security / abuse

- PR workflows: no `pull_request_target`; no deployment secrets passed into PR jobs (`PR secret guard` job greps `.github/workflows`).
- Health endpoint does not reflect query strings or headers into logs/body.
- Fixture/seed data contains no live credentials.
- Migration SQL is repo files only; runner does not execute caller-supplied SQL strings from the network.
- N/A for this issue: CSRF, magic-link replay, SSRF of user URLs, webhook forgery (no such features yet).

## Accessibility

- Smoke: each public page has exactly one `h1` (or a documented exception) and a header `<nav>` reachable before main content.
- Full axe/keyboard audit is **N/A as a merge blocker** for #4 (belongs to #9). Record any obvious smoke failures and fix them.

## Performance / load

- N/A as a merge blocker. Migration of empty + prototype-sized (≤10 companies) data should complete in < 5s locally; record duration. No 500-company load in this issue.

## Failure / recovery

- Checksum mismatch → non-zero exit, no later migration applied.
- Postgres unavailable during migrate → non-zero exit, no truncated ledger.
- DB down while web is up → health 503 degraded, public pages must not crash the Node process (existing try/catch empty rendering remains until a later issue replaces it; health must not swallow the error as `ok`).
- Redis unavailable locally → Redis integration skipped; CI Redis down → job fails.

## Observability / rollback

- Migrate logs version, name, and duration; does not log SQL body at info level (avoid huge policy-unrelated noise; never log connection passwords).
- Rollback: revert the PR / deploy previous worker; schema is additive (`IF NOT EXISTS`) so old code keeps reading existing tables. Document that unused `schema_migrations` is harmless.
- Feature switches N/A (no new product features).

## Prerequisites and cleanup

- Postgres reachable via `TEST_DATABASE_URL` or local peer/password URL. Tests create and drop `privacyradar_test_*` databases when they manage lifecycle; CI uses the service database and truncates tables between tests.
- Redis via `TEST_REDIS_URL` in CI (`redis://localhost:6379/0`).
- Playwright browsers installed in CI with `npx playwright install --with-deps chromium`.
- Do not commit `.coverage`, `test-results/`, `playwright-report/`, or `/tmp/reviewcheckpoint.json`.
- Drop leftover local `privacyradar_test_*` databases after the suite (fixture finalizer).

## Exact local commands (CI-equivalent)

```bash
cd worker
python -m pip install -e '.[dev]'
ruff check privacyradar tests
mypy privacyradar
pytest

cd ../web
npm ci
npm run lint
npx tsc --noEmit
npm run build
npx playwright install chromium
npm run test:e2e
```

Database job equivalent:

```bash
privacyradar migrate
privacyradar migrate
```
