# PrivacyRadar Implementation Test Plan

## Quality gates

- Python and TypeScript lint/type checks pass.
- Worker statement coverage cannot regress below the floor in `worker/pyproject.toml` (`--cov-fail-under`).
- Domain coverage is at least 90%; evidence validation, authorization, state transitions, notification deduplication, and entitlement checks have 100% branch coverage.
- The labeled material-change set reaches at least 95% precision before automatic publication.
- Every public claim passes quote-anchor, context, company, region, and snapshot validation.
- The critical Playwright journeys pass at 320px and desktop widths. Issue #4 ships a public smoke subset; later issues expand it.

## Suites

### Worker unit tests

- Normalization, Unicode, headings, blank content, section collisions, and deterministic hashes.
- Fetch result classification for DNS, TLS, timeout, redirects, status codes, wrong type, short content, and extraction failures.
- Source, event, notification, and correction transition functions including forbidden transitions.
- Taxonomy parsing, negation, quote anchoring, surrounding context, and unsupported claim rejection.
- Retry schedules, lease expiry, quarantine thresholds, and per-domain concurrency.

### Worker integration tests

- Disposable Postgres migrations from empty and current prototype schemas.
- Concurrent source claims and snapshot deduplication.
- Transactional snapshot/event/evidence/outbox creation and rollback.
- Model timeout, refusal, invalid structured output, missing citations, and fallback behavior.
- Provider webhook signature verification and duplicate delivery handling.

### Web unit and component tests

- Search combobox keyboard and screen-reader behavior.
- Watch button optimistic, unauthorized, conflict, and recovery states.
- Freshness, region mismatch, partial comparison, evidence context, action eligibility, and correction banners.
- Email HTML/text rendering with long values, images disabled, dark mode, and unsubscribe content.

### Browser tests

- Search → profile → anonymous Watch → magic link → restored selection → preferences → My Radar.
- Same-device and cross-device magic links; expired, replayed, and abandoned flows.
- Watch/unwatch double clicks, back navigation, expired sessions, and slow requests.
- Desktop and mobile comparison with incomplete and mismatched-region evidence.
- Alert link → evidence → external action → return state.
- Correction submission and published amendment.
- Assistant ask, stream, stop, retry, refusal, rate limit, and citation focus.
- Account export and deletion.
- Database/service failures show explicit error states rather than empty content.

### Evaluation suites

- At least 200 labeled old/new policy pairs balanced across material, cosmetic, uncertain, truncation, navigation churn, and regional changes.
- Extraction fixtures cover every taxonomy category plus absent, conflicting, conditional, and negated disclosures.
- Prompt-injection corpus treats all policy content as hostile instructions.
- Citation eval verifies exact/normalized quote presence and surrounding clauses.
- Assistant eval measures grounded material sentences, refusal accuracy, retrieval completeness, and cost.

### Load and operational tests

- 2,000 due sources with bounded fetch/browser pools and per-domain limits.
- Alert fan-out bursts with worker crashes, lease expiry, retries, and zero duplicate deliveries.
- Queue lag and freshness alerts fire under deliberate degradation.
- Backup restore, source quarantine, publication rollback, correction, key rotation, and provider outage runbooks are exercised.

## Manual release checklist

- Review 25 wedge-company profiles against their source policies.
- Confirm every action URL, region, and last-checked date.
- Test VoiceOver and keyboard-only flows.
- Review PrivacyRadar’s own privacy notice and data retention behavior.
- Send seed alerts to internal addresses across major email clients.
- Confirm feature switches disable publication, notifications, assistant, and new company cohorts independently.
