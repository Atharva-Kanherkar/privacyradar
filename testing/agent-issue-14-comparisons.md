# agent-issue-14-comparisons — Test Contract

Issue: https://github.com/Atharva-Kanherkar/privacyradar/issues/14
Parent epic: https://github.com/Atharva-Kanherkar/privacyradar/issues/2
Depends on: #8, #9, #13 (merged). Base: `main` at `61b372a`.

This contract is locked before implementation. If requirements change, update and commit this file separately before changing code.

## Outcome

Consumers compare 2–4 companies on published, evidence-backed disclosures. Comparison is a decision aid, not a score, not legal advice, and not a substitute for reading the policy.

## Non-goals

- An overall privacy score or ranked “winner”
- Querying `candidate_claims` or `extraction_runs` from the browser or from `web/src/lib/db.ts`
- Saved named comparisons (URL is the shareable state)
- Billing (#16), assistant (#15), closing #3, claiming 500 companies

## Invariants

1. Only **published** claims from the latest non-rolled-back revision are compared.
2. Direct comparison requires the **same taxonomy version**. Mixed versions render `not_comparable`, not a blended matrix that looks complete.
3. Compatible region is required for an unqualified comparison. Mixed source regions keep the matrix but mark `region_mismatch` conspicuously. Unknown stays unknown.
4. A missing cell is `not_found_in_evidence`. That is never presented as a favorable “does not collect / does not share.”
5. Every displayed value that is not unknown links to published quote evidence (company page claim anchor).
6. No overall score field exists in the page, JSON, or worker payload.
7. Shareable canonical URL: `/compare?companies=slug-a,slug-b` (2–4 unique slugs, stable order as submitted).

## Schema (migration `0010`)

Additive. Ledger **10**. Required public tables remain **38**.

- `publication_revisions.taxonomy_version text not null default '1.0.0'` so public compare queries do not join `extraction_runs`
- `product_events.name` also allows `compare_start`, `compare_complete`, `compare_evidence`

`db/schema.sql` includes these objects. Do not change checksums of 0001–0009.

## Functional behavior

- `GET /compare` with fewer than 2 valid slugs prompts the user to select companies. No fake empty matrix.
- `GET /compare?companies=signal,proton` shows a dimension×company table (desktop) and stacked-per-dimension cards (mobile CSS). Dimensions: `sensitive`, `sharing`, `purpose`, `retention`, `control`, `data_collected`.
- Company picker is a GET form (checkboxes / add slug) that 303/redirects to the canonical `companies=` URL. Maximum 4; extras dropped with a visible note.
- Column headers show company name, source region, and freshness. Stale/degraded/quarantined is visible. Corrected publication is labeled when `publication_state = 'corrected'` exists for that company.
- `GET /api/compare?companies=a,b` returns the same published-only payload. Body never contains `candidate_claims`, `extraction_runs`, or unpublished headlines.
- Selecting 2+ companies records `compare_start`; rendering a full comparable matrix records `compare_complete`; opening evidence records `compare_evidence`. Anonymous events may have null `user_id`.
- Company profile includes a Compare control that starts `/compare?companies={slug}`.
- Copy: “Not found in evidence” and “Not legal advice.” Never “takes.”

## Unit tests

- `test_compare_requires_two_to_four_companies`
- `test_compare_unknown_cell_is_not_favorable`
- `test_compare_mixed_taxonomy_is_not_comparable`
- `test_compare_mixed_region_is_conspicuous`
- `test_compare_payload_has_no_score`

## Integration

- `test_migrate_fresh_includes_0010` (ledger 10, 38 tables)
- `test_public_pages_sql_ignores_candidates` still forbids `extraction_runs` in `db.ts`
- `test_seed_public_fixtures_publishes_signal_claim` plus a second fixture company `proton` with a different published dimension

## E2E

- User selects Signal and Proton, lands on `/compare?companies=signal,proton`, sees a difference, opens evidence, sees no overall score.
- Axe: table has row/column headers (`scope` or `id`/`headers`).

## Security

- Compare is public (no auth required).
- Queries use published revisions only.
- Product events store slugs/ids, not emails or quotes.
