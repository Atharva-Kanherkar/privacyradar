# agent-issue-13-catalog-cohorts — Test Contract

Issue: https://github.com/Atharva-Kanherkar/privacyradar/issues/13
Parent epic: https://github.com/Atharva-Kanherkar/privacyradar/issues/2
Depends on: #5–#8 (merged). Base: `main` at `a22acd5` (#12).

This contract is locked before implementation. If requirements change, update and commit this file separately before changing code.

## Outcome

Catalog expansion is **demand-ranked and quality-gated**. Size is not success. The product either reaches 500 **healthy** companies or **stops earlier with a documented gate**. This issue does **not** bypass publication review and does **not** invent 500 healthy profiles.

## Non-goals

- Claiming 500 healthy companies without two measured crawl/publication cycles
- Monitoring arbitrary user-submitted URLs (SSRF / abuse)
- Billing (#16), assistant (#15), closing #3

## Invariants

1. A company is catalog-eligible only with slug, name, official website, category, official privacy URL, explicit region, and cohort.
2. `privacyradar catalog-validate` rejects duplicate slugs, duplicate privacy hosts, SSRF/private URLs, missing fields, and confusable lookalike hosts (`rn`/`m`, punycode mix).
3. Cohorts other than `seed` stay **disabled** until `catalog_cohorts.enabled` is true. Disabled cohorts are not seeded as crawl sources.
4. Public nominations are labeled **requested, not monitored**. No promised date.
5. Duplicate nominations (same registrable website host as an existing company or open request) mark `duplicate`, never a second crawl target.
6. Publication review is unchanged. Fetch failure is not an empty policy.
7. Health CLI reports fetch success, quarantined count, and evidence-validation pass rate **without** claiming the 500-company gate has passed unless the numbers meet the thresholds for two recorded cycles.

## Schema (migration `0009`)

Additive. Ledger **9**. Required public tables **38**.

- `catalog_cohorts(key text pk, enabled boolean not null, target_n int not null, notes text, updated_at)`
  - seed `seed` enabled, target 10; `c1` disabled, target 25
- `company_requests(id uuid pk, name text, website text not null, category text, status text not null, duplicate_of uuid, created_at)`
  - `status in ('requested', 'duplicate', 'accepted', 'declined')`
- `catalog_health_snapshots(id uuid pk, fetch_success_pct numeric, evidence_valid_pct numeric, created_at)`
- `companies.cohort text not null default 'seed'`
- `companies.owner text not null default 'unassigned'`
- `product_switches` unchanged; cohort enablement is `catalog_cohorts.enabled`

`db/schema.sql` includes these objects.

## Functional behavior

- `GET /companies/request` explains that a nomination is not monitoring.
- `POST /companies/request` (form: name, website, category) inserts `requested` or `duplicate`. 303 to `/companies/request?status=received` or `duplicate`.
- YAML catalog may include extra official companies in cohort `c1`. Seed skips `c1` while disabled.
- `privacyradar catalog-validate` exits 1 on invalid YAML.
- `privacyradar catalog-health` prints counts: companies, sources, healthy, degraded, quarantined, fetch_success_pct, evidence_valid_pct, gate=`stop` until two cycles meet ≥95% fetch success and ≥98% evidence-validation.
- `docs/CATALOG_GATES.md` records the stop: we do not claim 500.

## Unit tests

- `test_catalog_validate_rejects_duplicate_hosts`
- `test_catalog_validate_rejects_ssrf_and_confusable_hosts`
- `test_seed_skips_disabled_cohort`
- `test_request_dedupes_existing_company_host`

## Integration

- `test_migrate_fresh_includes_0009` (ledger 9, 38 required tables)
- `test_catalog_health_gate_is_stop_without_two_cycles`

## E2E

- `/companies/request` submits a nomination and shows “requested, not monitored”.
- Duplicate website against Signal shows duplicate status, not a crawl promise.

## Security

- Nomination websites are not fetched from the public form.
- SSRF classification still runs on catalog seed URLs.
