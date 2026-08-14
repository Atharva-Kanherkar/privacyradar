# agent-issue-15-cited-assistant — Test Contract

Issue: https://github.com/Atharva-Kanherkar/privacyradar/issues/15
Parent epic: https://github.com/Atharva-Kanherkar/privacyradar/issues/2
Depends on: #8, #9 (merged). Base: `main` at `44d5b42` (#14).

This contract is locked before implementation. If requirements change, update and commit this file separately before changing code.

## Outcome

A **company-scoped** cited assistant answers narrow questions from **published** claims and evidence only. It ships behind a kill switch and an evaluation gate. Static search and evidence pages remain fully usable when the assistant is off. This issue does **not** enable the assistant in production.

## Non-goals

- A general chatbot, legal advice, or on-demand crawler
- Consumer model picker
- Enabling `product_switches.assistant` in production or CI Browser smoke
- Billing (#16), closing #3, claiming launch-ready (#17)

## Invariants

1. No citation ⇒ no factual answer. Empty citations must `refuse`.
2. Retrieval is published revisions for the selected company only. Cross-company leakage is a hard fail.
3. Policy text is untrusted data, never instructions. The assistant has no tools and cannot publish or edit claims.
4. `product_switches.assistant = false` by default. Feature-off returns `disabled` and does not call a model provider.
5. `ASSISTANT_PROVIDER=fake` is the default. CI must not call OpenAI.
6. Out-of-scope questions (other companies, weather, legal conclusions) are refused with a link to the company page.
7. Rate limit: 10 questions / day / identity (session user id, else hashed IP). Raw questions are not stored.

## Schema (migration `0011`)

Additive. Ledger **11**. Required public tables **39**.

- `product_switches` seed `assistant=false`
- `assistant_usage(identity_hash text, day date, count int, unique(identity_hash, day))`

`db/schema.sql` includes these objects.

## Functional behavior

- Company page shows an assistant panel. When the switch is off, copy explains it is off and published disclosures remain.
- `POST /companies/[slug]/ask` (form: `question`) returns 303 to the company page with `?ask=disabled|refused|answered|limited`.
- Answer text, when present, includes clickable claim anchors and quotes from published evidence.
- `privacyradar eval-assistant` runs the golden corpus with the fake provider and exits 1 if citation or refusal gates fail.
- `docs/ASSISTANT_GATES.md` and `docs/adr/0001-assistant-routing.md` record the provider/routing decision and the off-by-default gate.

## Unit tests

- `test_assistant_disabled_does_not_answer`
- `test_assistant_refuses_without_citation`
- `test_assistant_answers_only_with_published_quote`
- `test_assistant_isolates_company_retrieval`
- `test_assistant_rate_limit`

## Integration

- `test_migrate_fresh_includes_0011` (ledger 11, 39 tables)
- `test_eval_assistant_gates_pass_on_golden_fake`

## E2E

- Company page with assistant off still shows Signal’s published quote.
- Asking a question while off does not invent an answer.

## Security

- No tools, no arbitrary URL fetch, no other user’s watches.
- Logs must not include raw questions or emails.
