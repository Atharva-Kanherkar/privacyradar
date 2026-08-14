# agent-issue-8-publication-corrections — Test Contract

Issue: https://github.com/Atharva-Kanherkar/privacyradar/issues/8
Parent epic: https://github.com/Atharva-Kanherkar/privacyradar/issues/2
Depends on: #7 (merged PR #21 / `cb11c469855f5d02383ed35cf98cf43930f4d1c6`) and #5.
Base: `main` at `cb11c469855f5d02383ed35cf98cf43930f4d1c6`

This contract is locked before implementation. If requirements change, update and commit this file separately before changing code.

## Outcome

Consumers only see defensible claims. Extraction output from #7 stays untrusted until a validator plus an attributable publication revision says otherwise. Invalid or missing evidence cannot be published. Corrections supersede; they never silently edit.

## Non-goals

- Public UX redesign, evidence drawers, or methodology page layout (#9).
- Passwordless auth / Better Auth sessions (#10). Reviewer identity is the existing operator `actor` token (`cli:local`), not a user id from a request body.
- Notification outbox delivery (#12). Do not enqueue alerts from unpublished or rejected candidates.
- Assistant (#15), comparisons (#14), billing checkout (#16), catalog dump (#13).
- Live OpenAI in CI. Materiality eval uses a documented heuristic plus a labeled synthetic corpus.

## Invariants

1. Public `web/src/lib/db.ts` selects change events only in `published` or `corrected`. It never selects `candidate_claims`, `extraction_runs`, or unpublished revisions.
2. A published claim must resolve to company, source, observation, snapshot, verbatim quote/span, extraction run, publication revision, and timestamps.
3. Missing quote, stale/wrong offsets, wrong snapshot ownership, invalid taxonomy shape, or `validation_state != valid` cannot become a published claim (service layer and database checks).
4. Publication revisions, published claims, and review actions are append-only. Correction **state** may UPDATE, but every transition inserts a `review_actions` row. Rollback inserts a new revision; it does not UPDATE an old revision.
5. Every publish/reject/rollback/correct action records `actor` matching `^[a-z0-9][a-z0-9:_-]{1,62}$`. Emails and URLs are rejected.
6. `product_switches.publication = false` refuses publish and rollback (safe feature-off). Existing published rows remain readable.
7. Fetch failure still does not create a publication. No observation / invalid snapshot → no revision.
8. No secrets, DSNs, policy bodies, or emails in CLI/logs/metrics.
9. Golden materiality pairs are synthetic `.test` policies, not third-party copyrighted pages.
10. #3 remains open. Paid checkout stays disabled.

## Documented budgets / gates

| Name | Value |
|---|---|
| Materiality corpus size | **200** labeled old/new pairs |
| Heuristic precision on that corpus | **≥ 0.95** (CI fail under) |
| Auto-publish | **off**. Material/uncertain events enter `review_pending`. Only `privacyradar publish-run` / `publish-event` can reach `published`. |
| Cosmetic events | `rejected` (retained, not public) |
| Citation for published claims | exact or whitespace-normalized quote in the snapshot; offsets must match that span |
| Ledger after `0005` | **5** |
| Live OpenAI in CI | forbidden |

Rollback: set `publication` switch false; leave tables. Public pages keep last published revisions. No down-migration.

## Functional Behavior

### Schema (migration `0005`)

Additive. `0001`–`0004` checksums unchanged.

- `change_events.publication_state` text not null, check in (`detected`,`analyzing`,`review_pending`,`published`,`rejected`,`failed`,`corrected`). Existing rows backfill `published`; new inserts default `detected`. `published_at` becomes nullable; set only on publish.
- `publication_revisions(id, company_id, observation_id, extraction_run_id, change_event_id, rolls_back_id, revision_n, state, actor, created_at)` state in (`published`,`rolled_back`). Unique `(company_id, revision_n)`. `rolls_back_id` is set only on `rolled_back` rows.
- `published_claims(id, revision_id, candidate_claim_id, claim_key, category, attribute, polarity, quote, snapshot_id, start_offset, end_offset)` unique `(revision_id, claim_key)`.
- `review_actions(id, actor, action, target_type, target_id, reason, created_at)` action in (`approve`,`reject`,`publish`,`rollback`,`correct`,`acknowledge`,`decline`).
- `corrections(id, company_id, target_revision_id, replacement_revision_id, reporter_kind, state, public_note, actor, created_at, resolved_at)` state in (`submitted`,`acknowledged`,`reviewing`,`corrected`,`declined`).
- `product_switches(key text pk, enabled boolean not null, updated_at)` seed `publication=true`.

Append-only triggers on `publication_revisions`, `published_claims`, and `review_actions`. `corrections` may UPDATE `state`, `replacement_revision_id`, `actor`, `public_note`, and `resolved_at` only; DELETE is forbidden. `product_switches` may UPDATE `enabled` and `updated_at`.

`db/schema.sql` includes these objects. Required-tables CI count includes the five new tables. Ledger count **5**.

### Validator

`validate_claim_for_publication(conn, candidate_claim_id) -> ok | error_code`.

Error codes: `missing_claim`, `unsupported`, `invalid_category`, `quote_missing`, `offset_mismatch`, `snapshot_mismatch`, `observation_mismatch`, `empty_quote`.

Offsets: if stored offsets are null, compute from `markdown.find(quote)`; if they are set, they must equal that span (or the whitespace-normalized span).

### Publication

`publish_run(conn, run_id, *, actor)`:

1. Switch `publication` must be on.
2. Load run + observation + snapshot. Invalid/missing snapshot → refuse, no revision.
3. Validate every `validation_state=valid` claim. Any failure → no revision, `review_actions` with reject reason, event stays `review_pending` or `failed`.
4. In one transaction: take advisory lock `pg_advisory_xact_lock(8462017)`, insert `publication_revisions` with `state='published'` and next `revision_n` for the company, insert `published_claims` for each validated claim. Current publication for a company is the latest `published` revision that is not the target of a later `rolls_back_id`. Historical revision rows are never updated.
5. If a `change_event_id` is linked, UPDATE that event to `publication_state='published'` and `published_at=now()`. `change_events` is **not** append-only (existing table, no new trigger). Revisions are the immutable evidence record.
6. Cosmetic materiality → `publication_state=rejected`, not listed publicly, no published claims.
7. Uncertain/material → `review_pending` until an operator publishes.

Rollback inserts a `publication_revisions` row with `state='rolled_back'` and `rolls_back_id` pointing at the abandoned revision. If another current published revision remains, rollback then inserts a new `state='published'` row cloning that prior revision's claims. If the abandoned revision was the only current publication, rollback does not clone; the company has no current published claims. In both cases, if the abandoned revision is linked to a change event that is not restored as current, that event is set to `publication_state='corrected'` so it is history, not a live feed item. Review actions record `rollback`.

### Corrections

`submit_correction` → `submitted`. `acknowledge_correction` → `acknowledged`. `resolve_correction(..., decision=corrected)` publishes a replacement revision and sets correction `corrected` with `replacement_revision_id`. `declined` does not change current publication. Public note is required for `corrected`. Prior revision remains readable.

### CLI

```
privacyradar publish-run RUN_ID --actor ACTOR
privacyradar reject-event EVENT_ID --actor ACTOR --reason CODE
privacyradar rollback-revision REVISION_ID --actor ACTOR --reason CODE
privacyradar correction-submit --company-id ID --revision-id ID --note TEXT --actor ACTOR
privacyradar correction-resolve CORRECTION_ID --actor ACTOR --decision corrected|declined --note TEXT
privacyradar publish-stats
privacyradar eval-materiality
```

`publish-stats` prints counts only: `review_pending`, `published_revisions`, `rollbacks`, `citation_failures`, `queue_age_seconds`, `corrections_open`. No URLs, quotes, or emails.

### Public reads

`listEvents` (home and RSS): `publication_state = 'published'` only. Company change history: `publication_state in ('published','corrected')` so replacement history stays inspectable. Company profile may keep reading `extractions.practices` for the prototype practices JSON until #9, but must not read candidate tables. A helper `listPublishedClaims(companyId)` is available for #9 and is unused by pages except tests that grep `db.ts`.

### Materiality corpus

`worker/eval/materiality/pairs.jsonl` — 200 objects `{id, label, old, new}` with `label` in `material|cosmetic|uncertain`. Templates cover date-only, nav/footer, sale added, retention added, deletion weakened, regional clause, truncation, and ambiguous “may share”.

`privacyradar eval-materiality` and `pytest tests/test_materiality_eval.py` fail if `n < 200` or precision < 0.95.

## Unit Tests

- `test_quote_missing_cannot_publish`
- `test_offset_mismatch_cannot_publish`
- `test_unsupported_claim_cannot_publish`
- `test_snapshot_mismatch_cannot_publish`
- `test_invalid_actor_rejected`
- `test_publication_switch_off_refuses_publish`
- `test_cosmetic_event_is_rejected_not_listed`
- `test_forbidden_publication_transition`

## Integration / Functional Tests

- `test_migrate_fresh_includes_0005` (ledger 5, 0001 checksum pin)
- `test_publish_run_is_atomic` (validator fail → zero published_claims and no revision)
- `test_concurrent_publish_serializes` (advisory lock; one winner)
- `test_rollback_preserves_prior_revision_row`
- `test_correction_creates_replacement_revision`
- `test_review_actions_are_append_only`
- `test_public_sql_ignores_unpublished_and_candidates`
- `test_materiality_corpus_meets_gates`
- `test_malformed_model_output_cannot_publish`

## Smoke Tests

- `privacyradar eval-materiality` prints metrics, no policy body, no DSN.
- `privacyradar publish-stats` prints integer counts.
- Coverage floor unchanged (75%).

## E2E Tests

Playwright: seed one unpublished `review_pending` material event with a unique headline; home and `/feed.xml` must not contain that headline. Existing Signal smoke remains.

## Manual / cURL Tests

```
privacyradar migrate
privacyradar eval-materiality
privacyradar publish-stats
# no postgresql:// and no policy quotes
```

## Observability

Logs: `run_id`, `revision_id`, `actor`, `n_claims`, `error_code`. Never log quotes or markdown.

## Security / privacy

- No public mutation routes in this issue.
- Actor is never taken from an unauthenticated HTTP body.
- Unpublished candidates stay off RSS and home.
