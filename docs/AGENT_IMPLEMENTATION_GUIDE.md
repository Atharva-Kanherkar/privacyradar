# PrivacyRadar Agent Implementation Guide

This file is the operating contract for an AI coding agent assigned to a PrivacyRadar roadmap issue.

## Read this first

Before changing code, read:

1. The assigned GitHub issue in full, including parent epic and dependencies.
2. [`PRODUCT_PLAN.md`](PRODUCT_PLAN.md), especially Product principles, Engineering review, Strict roadmap, and Failure modes.
3. [`TEST_PLAN.md`](TEST_PLAN.md).
4. The current implementation files explicitly named by the issue.
5. `README.md`, `db/schema.sql`, `worker/pyproject.toml`, and `web/package.json` when the task crosses those boundaries.

If the issue conflicts with the product plan, stop and document the conflict on the issue. Do not silently reinterpret the product.

## Non-negotiable invariants

1. The product is for consumers. Do not introduce workspaces, seats, procurement, audit exports, or enterprise compliance workflows.
2. Call policy-derived facts `disclosed practices`. A policy does not prove actual company behavior.
3. Every published material claim must identify its company, source, region, snapshot, evidence span, taxonomy version, prompt/model version, and publication revision.
4. Fetch or extraction failure must never replace the last successful policy observation.
5. Detection is durable before any model call. A process crash must not lose a policy change.
6. Empty, short, wrong-type, non-2xx, or error-page content is a failed attempt, never a valid snapshot.
7. User identity comes only from a validated server session. Never accept a user ID from a mutation body.
8. Notifications are deduplicated by a database constraint and delivered from a transactional outbox.
9. Policy text and user questions are untrusted model input. Models get no tools or secrets.
10. Public facts and evidence stay free. Billing may gate convenience, automation, and allowances only.

## Issue execution protocol

### 1. Confirm readiness

- Verify every `Depends on` issue is closed or its required contract is already merged.
- Pull the current default branch and inspect migrations already present.
- Restate the issue outcome and acceptance criteria in your implementation notes.
- If external provider credentials are needed, implement and test through an adapter; do not block local tests on live credentials.

### 2. Write the test diagram first

For every new flow, list:

```text
happy path
missing/nil input
empty input
upstream failure
duplicate/retry path
authorization boundary
rollback or feature-off behavior
```

Map each branch to a unit, integration, browser, evaluation, or load test. Add the tests in the same PR as the behavior.

### 3. Implement one vertical contract

- Prefer explicit domain functions and typed outcomes over broad exception handling.
- Keep Python worker state and TypeScript web state ownership aligned with the architecture plan.
- Use additive, forward-only migrations. Migration execution must be repeat-safe under the migration tool.
- Preserve old reads during backfill and rolling deployment.
- Add structured context to errors: run, source, snapshot, event, user-safe code, retry decision.

### 4. Validate locally

Run all commands that apply:

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

Database and fixtures:

```bash
privacyradar migrate
privacyradar migrate   # no-op when already at head
privacyradar seed-fixtures
```

`pytest` creates ephemeral PostgreSQL databases against local Postgres or `TEST_ADMIN_DATABASE_URL`. Redis tests require `TEST_REDIS_URL` (required in CI; skipped locally if Redis is down). Playwright global setup runs `migrate` and `seed-fixtures` using `DATABASE_URL`.

Troubleshooting:

- `checksum mismatch for migration` — an applied SQL file changed. Restore the original file or add a new numbered migration; never edit applied SQL.
- Browser smoke 503/unconfigured — `DATABASE_URL` must be the same for `privacyradar` and Next.js.
- Integration tests skip Postgres — export `TEST_ADMIN_DATABASE_URL` to a superuser URL that can `CREATE DATABASE`.
- Do not use `pull_request_target` or interpolate deployment secrets into PR workflows. See [`BRANCH_PROTECTION.md`](BRANCH_PROTECTION.md).

For database work, start a disposable PostgreSQL 16 instance, apply all migrations from an empty database (`privacyradar migrate`) and from the last released/prototype schema, then run integration tests. For queue work, test against Redis 7.

### 5. Produce an auditable handoff

The PR description must contain:

- Issue and parent epic links.
- User-visible outcome.
- Data model/API/state-machine changes.
- Failure paths covered.
- Security/privacy impact.
- Tests and exact commands run.
- Migration, rollout, feature switch, and rollback behavior.
- Metrics/logs/runbook changes.
- Explicit follow-ups that remain out of scope.

## Definition of done

An issue is complete only when:

- Every acceptance criterion is demonstrably satisfied.
- CI passes without skipped required checks.
- Tests cover all named branches and failure modes.
- Documentation and diagrams match the implementation.
- No secret, personal data, policy token, or raw magic link is logged.
- Metrics make production success and failure visible.
- Feature rollout and rollback are safe under partial deployment.
- A reviewer can reproduce the behavior from the PR description.

“Code exists” is not completion. The user outcome, failure behavior, tests, observability, and deployment path must all exist.
