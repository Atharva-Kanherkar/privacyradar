# agent-issue-9-public-pages — Test Contract

Issue: https://github.com/Atharva-Kanherkar/privacyradar/issues/9
Parent epic: https://github.com/Atharva-Kanherkar/privacyradar/issues/2
Depends on: #8 (merged PR #22 / `608835b`)
Base: `main` at `608835b`

This contract is locked before implementation. If requirements change, update and commit this file separately before changing code.

## Outcome

A person can find a company, understand disclosed practices and a material change, inspect the exact quote, and see freshness — without an account. Public pages never render unpublished candidates. Uncertainty stays visible. There is no global privacy score.

## Non-goals

- Passwordless auth, Watch, My Radar (#10, #11). No Sign-in that pretends to work.
- Compare matrix (#14), assistant (#15), billing (#16), catalog dump (#13).
- Moderated usability sessions or production Core Web Vitals from real users (#3 / later gates). Do not invent those metrics.
- Live OpenAI. Pages read only publication-approved rows.
- Mutating public forms except a GET search query.

## Invariants

1. Public SQL never selects `candidate_claims` or `extraction_runs`. Company practices render from `listPublishedClaims` (current revision not targeted by `rolls_back_id`). Change pages render `change_events` in `published` or `corrected` only. Home/RSS remain `published` only.
2. If evidence quote/offsets cannot be resolved, the claim is omitted, not shown as empty truth.
3. Copy in structured factual UI uses “discloses”, “we found”, “we have not found evidence”, and “last checked”. Do not say a company “takes” data in those blocks. No universal grade.
4. Region and source URL are visible on the company profile. Ambiguous/missing region is labeled, not defaulted into a legal claim.
5. Unpublished fixture headline `UNPUBLISHED_FIXTURE_HEADLINE` is absent from `/`, `/changes`, `/feed.xml`, company pages, and change detail.
6. Public routes work without cookies. No user id in query strings.
7. #3 stays open. Paid checkout stays disabled.

## Documented budgets / gates

| Name | Value |
|---|---|
| Search | GET `/companies?q=`; results from `queryCompanies`; no client-side secret |
| Interactions to evidence | Search → profile → in-place evidence (`<details>`). Profile shows the first quote without a fourth navigation. |
| axe | `@axe-core/playwright` on `/`, `/companies`, `/companies/signal`, `/changes`, `/methodology` — **zero serious/critical** |
| Keyboard | Skip link, visible `:focus-visible` ring, all nav links reachable |
| Zoom | 200% layout does not clip primary headings (Playwright viewport assertion) |
| Reduced motion | `prefers-reduced-motion: reduce` disables non-essential animation |
| Performance | Public pages are server-rendered; no third-party ads/analytics scripts in this issue |
| Auth | none |

## Functional Behavior

### Design system

`docs/DESIGN.md` locks tokens: paper, ink, muted, rule, surface, focus, important, warning, success; 4px spacing; 44px minimum tap target; 2px focus ring. Components used by pages live under `web/src/components/`.

### Routes

| Path | Behavior |
|---|---|
| `/` | Search field (GET `/companies`) + recent **published** material changes + catalog sample |
| `/companies` | Searchable catalog; `?q=` filters; region + last checked + health |
| `/companies/[slug]` | Name, category, region, source link, freshness, disclosed practices from published claims, material changes, correction history link |
| `/changes` | Chronological published material changes |
| `/changes/[id]` | Headline, summary, quotes, company link, published time; 404 if unpublished/missing |
| `/methodology` | How capture, hash, review, and correction work. Honest limits. |
| `/corrections` | Public corrected/declined rows with `public_note` |
| `/about` | Redirects to `/methodology` |
| `/sitemap.xml` | Indexable public URLs only |
| `/robots.txt` | Allows `/` and sitemap |

Missing company/change → 404 page with a way back to catalog. Database errors → explicit unavailable copy, not an empty catalog presented as “no companies exist”.

### Evidence

Each published claim is a disclosure row (category, attribute, polarity) with an evidence `<details>` containing the verbatim quote, snapshot id (mono), revision n, and source region. Deep link: `/companies/[slug]#claim-{claim_key}`.

### Freshness / health

Labels: `last checked {date}` or `not yet checked`. Health `degraded`/`quarantined` → `check delayed`. Never imply a failed fetch is an empty policy.

## Unit Tests

- `test_public_pages_sql_ignores_candidates` — `web/src/lib/db.ts` has no `candidate_claims` / `extraction_runs`; company practices query uses `published_claims`.
- `test_seed_public_fixtures_publishes_signal_claim` — seed inserts a current published claim for Signal and a published event whose headline is not the unpublished fixture.

## Integration / Functional Tests

- Existing worker suite still passes (coverage floor unchanged).
- `queryCompanies` / `getChangeEvent` refuse unpublished ids (404/null).

## Smoke Tests

- `npm run lint`, `npx tsc --noEmit`, `npm run build`
- `/api/health` unchanged; no DSN in JSON

## E2E Tests

Playwright (desktop + 320px project for axe on home/company):

- Home search can reach Signal in two further activations (submit + company link).
- Company profile shows published email disclosure quote; unpublished headline absent.
- `/changes/{published-id}` shows the published fixture headline; unpublished id 404s.
- `/methodology` has a level-1 heading.
- axe-core serious/critical = 0 on the listed routes.
- Keyboard: skip link is the first focusable control.

## Manual / cURL Tests

```
curl -sI http://127.0.0.1:3000/methodology
curl -s http://127.0.0.1:3000/sitemap.xml | head
curl -s http://127.0.0.1:3000/api/companies/signal
# no postgresql://, no candidate_claims
```

## Observability

No new PII logs. Change and company pages do not print policy bodies to server logs.

## Security / privacy

- No public mutation routes.
- Quotes on public pages are from published claims only.
- Canonical URLs do not include session tokens.
