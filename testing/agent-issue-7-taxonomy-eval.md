# agent-issue-7-taxonomy-eval — Test Contract

Issue: https://github.com/Atharva-Kanherkar/privacyradar/issues/7
Parent epic: https://github.com/Atharva-Kanherkar/privacyradar/issues/2
Depends on: #5 (merged) and #4. Overlaps #6 after observation contracts (merged PR #20 / `7da3863`).
Base: `main` at `7da386305931d5d15a593ade63c33005b886ad13`

This contract is locked before implementation. If requirements change, update and commit this file separately before changing code.

## Outcome

Produce structured, consumer-actionable **candidate** claims from a complete policy, with measured quality. Taxonomy is versioned. Extraction runs are append-only and tied to an observation. Outputs stay untrusted until validation/publication (#8). Tests never call a live model and never crawl real companies.

## Non-goals

- Publication revisions, review queues, corrections, or exposing candidates on public pages (#8).
- Public UX redesign (#9), auth (#10), alerts (#12), comparisons (#14), assistant (#15), billing (#16).
- A 200-pair old/new materiality corpus (TEST_PLAN; owned with #8 publication gates). This issue ships an **internal synthetic extraction golden** covering every taxonomy category plus adversarial/long/empty/ambiguous cases.
- Chatbot / user-supplied extraction prompts.
- Replacing the existing `extractions.practices` JSON used by the public company page. Public reads stay on publication-approved data; #7 writes candidate tables only.

## Invariants

1. Public claims still come only from approved publication revisions. Candidate rows are not selected by `web/src/lib/db.ts`.
2. Every candidate claim has exact evidence spans (verbatim quote) in the source observation markdown. Missing quote → `unsupported`, not stored as valid.
3. Unknown is explicit (`polarity=unspecified` or category `uncertainty`). Absence of a claim is not proof of “does not collect.”
4. Same observation can be reprocessed under a new taxonomy version without overwriting old `extraction_runs`.
5. Claim keys are stable for the same taxonomy version + category + attribute + polarity.
6. Model/prompt/taxonomy versions are server-controlled (`settings.openai_extract_model`, module `PROMPT_VERSION`, `TAXONOMY_VERSION`). No request body can change instructions.
7. Policy text is untrusted: wrapped in delimiters; instructions are a code constant.
8. Fetch failure still does not create candidates. Extraction requires an existing observation + valid snapshot.
9. No secrets, emails, DSNs, or raw model dump in logs. Cost/latency are numbers.
10. Golden fixtures are synthetic `.test` policies, not third-party copyrighted pages.

## Documented budgets / gates (locked)

| Name | Value |
|---|---|
| Taxonomy version | `1.0.0` |
| Prompt version | `extract-1.0.0` |
| Chunk size | 4000 characters, 200 overlap, heading-aware |
| Max document chars to extractor | 120_000 (existing analyze cap) |
| Citation validity on golden | **1.0** (CI fail under) |
| Unsupported-claim rate on golden | **0.0** |
| Precision/recall on golden (matching adapter) | **≥ 0.99** overall |
| Eval latency budget (golden + fake extractor) | **< 5s** locally / CI |
| Cost on fake extractor | **0** |
| Live OpenAI in CI | forbidden |

Rollback: keep `0004` tables; stop writing new runs; public site unchanged. No down-migration.

## Functional Behavior

### Taxonomy `1.0.0`

Categories (closed set): `data_collected`, `purpose`, `sharing`, `retention`, `control`, `sensitive`, `region`, `uncertainty`.

Attributes (closed set, consumer-decision):

- data_collected: `email`, `name`, `phone`, `location`, `device_id`, `ip_address`, `browsing`, `purchase`, `payment`, `photos`, `voice`, `messages`, `account_activity`, `inferred_profile`, `other`
- purpose: `product`, `analytics`, `advertising`, `personalization`, `security`, `legal`, `ai_training`, `research`, `unspecified`
- sharing: `sale`, `third_party`, `advertising_partner`, `none_disclosed`
- retention: `duration_disclosed`, `unspecified`
- control: `deletion`, `opt_out`, `access`, `none_disclosed`
- sensitive: `biometrics`, `health`, `children`, `precise_location`, `none_disclosed`
- region: `global`, `EU`, `US`, `other`
- uncertainty: `unknown`

Polarity: `disclosed`, `negated`, `unspecified`.

`taxonomy_versions` row is immutable: `(version, schema_checksum)`. Checksum is SHA-256 of the canonical JSON category/attribute list. Changing the list requires a new version string.

### Schema (migration `0004`)

Additive. `0001`–`0003` checksums unchanged. CI ledger count **4**.

- `taxonomy_versions(version text pk, schema_checksum text not null, created_at)`
- `extraction_runs(id uuid pk, observation_id uuid not null references observations, snapshot_id uuid not null references snapshots, taxonomy_version text not null references taxonomy_versions, prompt_version text not null, model text not null, provider_request_id text, status text check in (`succeeded`,`failed`,`invalid`), confidence numeric, latency_ms integer, cost_usd numeric, created_at)` unique `(observation_id, taxonomy_version, prompt_version, model)` is **not** unique — re-runs are allowed as new ids; old rows stay.
- `candidate_claims(id uuid pk, run_id uuid not null references extraction_runs, claim_key text not null, category text not null, attribute text not null, polarity text not null, confidence numeric, validation_state text check in (`valid`,`unsupported`,`invalid_category`), payload jsonb not null default '{}')`
- `evidence_spans(id uuid pk, claim_id uuid not null references candidate_claims, snapshot_id uuid not null, quote text not null, section text, start_offset integer, end_offset integer, context text, validation_result text check in (`exact`,`normalized`,`missing`))`

Indexes: `extraction_runs(observation_id, created_at desc)`, `candidate_claims(run_id, claim_key)`.

Seed `taxonomy_versions` `1.0.0` inside `0004`. `db/schema.sql` includes these objects. Required tables count includes the four new tables.

### Extraction pipeline

1. Load observation → snapshot markdown. If missing/invalid, refuse (no run row with valid claims).
2. Chunk full document (heading-aware). A claim whose only evidence is after the first 4000 characters must still be found after reconcile.
3. Call extractor with **code** instructions + delimited untrusted document. Model id from settings, never from input.
4. Reconcile chunk outputs by `claim_key`; union evidence spans.
5. Validate each quote against snapshot markdown (exact substring, then whitespace-normalized). Fail → `unsupported` + `validation_result=missing`; do not count as valid.
6. Persist run + claims + spans in one transaction.

`privacyradar extract-observation OBSERVATION_ID` uses the adapter (live model only if `OPENAI_API_KEY` set; tests inject FakeExtractor).

### Evaluation runner

`privacyradar eval-extract` (and `pytest` golden suite) loads `worker/eval/golden/*.md` + `*.expected.json`.

Report fields: `precision_by_category`, `recall_by_category`, `citation_validity`, `unsupported_claim_rate`, `latency_ms`, `cost_usd`, `n_fixtures`.

CI: `pytest tests/test_eval.py` fails if gates are missed. No live HTTP.

## Unit Tests

- `test_taxonomy_checksum_stable_for_1_0_0`
- `test_claim_key_stable_across_runs`
- `test_claim_key_changes_when_taxonomy_version_changes`
- `test_unknown_attribute_rejected`
- `test_delimit_untrusted_wraps_policy_not_instructions`
- `test_quote_not_in_snapshot_is_unsupported`
- `test_negated_sale_is_not_disclosed_sale`
- `test_chunk_then_reconcile_finds_claim_only_in_last_section`
- `test_prompt_injection_in_policy_does_not_enter_instructions`
- `test_server_controlled_model_ignores_caller_model_override`

## Integration / Functional Tests

- `test_migrate_fresh_includes_0004` (ledger 4, 0001 checksum pin)
- `test_reprocess_same_observation_new_taxonomy_keeps_old_run`
- `test_extraction_run_is_append_only` (UPDATE/DELETE on runs rejected or unused; two inserts remain)
- `test_failed_observation_does_not_create_candidates`
- `test_golden_extraction_eval_meets_gates`
- `test_empty_policy_records_uncertainty_not_does_not_collect`
- `test_public_company_sql_does_not_select_candidate_claims`

## Smoke Tests

- `privacyradar eval-extract` prints integer/float metrics, no markdown policy body, no `OPENAI_API_KEY`.
- Worker pytest includes eval module. Coverage floor unchanged (75%).

## E2E Tests

N/A for public UX. Playwright must not grow a “candidates” page. Catalog still shows last verified observation, not raw candidates.

## Manual / cURL Tests

```
privacyradar migrate   # applies 0004
privacyradar eval-extract
# stdout like: citation_validity=1.0 unsupported_claim_rate=0.0 n_fixtures=N
# no postgresql:// and no policy quotes dumped
```

Live OpenAI extraction against a fixture observation is optional and out of CI.

## Observability

Logs: `run_id`, `observation_id`, `taxonomy_version`, `model`, `n_claims`, `n_unsupported`, `latency_ms`, `cost_usd`. Never log raw policy or quotes.

## Security / privacy

- No user prompt alters `EXTRACT_INSTRUCTIONS`.
- Candidates not in public JSON.
- Golden files use `@example.test` / `.test` hosts only.
