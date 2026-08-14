# agent-issue-11-watchlists — Test Contract

Issue: https://github.com/Atharva-Kanherkar/privacyradar/issues/11
Parent epic: https://github.com/Atharva-Kanherkar/privacyradar/issues/2
Depends on: #8 (publication) and #10 (auth, merged PR #24 / `f296dd1`)
Base: `main` at `f296dd1`

This contract is locked before implementation. If requirements change, update and commit this file separately before changing code.

## Outcome

An authenticated consumer can follow companies and see **My Radar**: a chronological feed of **published** material changes for companies they watch. Anonymous visitors can start a Watch and resume it after magic-link sign-in. No email is sent in this issue.

## Non-goals

- Transactional alerts / Resend (#12)
- Comparisons (#14)
- Assistant (#15)
- Billing (#16)
- Closing #3 or enabling paid checkout

## Invariants

1. Follow/unfollow identity comes only from the Better Auth session cookie. Never from a JSON `userId`.
2. My Radar lists only `change_events` with `publication_state = 'published'` for companies the viewer actively watches. Unpublished candidates never appear.
3. Duplicate follow requests for the same `(user_id, company_id)` create one active row.
4. Unfollow is immediate: the company disappears from My Radar and is not notification-eligible later (#12).
5. Account deletion (#10 function) also removes that user’s watches and product_events. Publication history stays.
6. Product events store event name, user id, company/event ids, and timestamp. They never store policy text, emails, magic-link URLs, or questions.
7. Watch intent `callbackURL` / `next` remains a same-origin path (`safeCallbackURL`).

## Schema (migration `0007`)

Additive. Ledger **7**.

- `watches(id uuid pk, user_id text not null, company_id uuid not null references companies, status text not null, source text not null, created_at, updated_at)`
  - unique `(user_id, company_id)`
  - `status in ('active', 'unwatched')`
  - `source in ('company_page', 'radar_onboarding', 'resume')`
- `product_events(id uuid pk, user_id text, name text not null, company_id uuid, event_id uuid, created_at)`
  - `name in ('follow', 'unfollow', 'radar_view', 'evidence_open')`
- `privacyradar_delete_consumer` also deletes `watches` and `product_events` for that user.

`db/schema.sql` includes these objects.

## Functional behavior

- Company page shows **Watch** when anonymous or not watching, **Watching** when active. Anonymous Watch goes to `/login?next=/companies/{slug}?watch=1`.
- After sign-in, `/companies/{slug}?watch=1` upserts an active watch from the session and redirects to the company page without the query flag.
- `POST /api/watches` body `{ "slug": "signal" }` (session required). Idempotent upsert `status=active`.
- `DELETE /api/watches/{slug}` sets `status=unwatched` (idempotent).
- `GET /radar` requires a session (else redirect `/login?next=/radar`). Shows published followed changes, newest first, plus watching list. Empty state explains how to add companies.
- `GET /radar/watching` lists followed companies with unfollow.
- Header: signed-in users see **My Radar** as a primary nav item. Do not label it Dashboard.
- Suggestions on empty radar: companies from the public catalog grouped by existing `category`, not inferred interest.

## Unit tests

- `test_follow_is_idempotent_for_same_user_company`
- `test_follow_rejects_missing_session_identity` (API / SQL helper never accepts a body user id)
- `test_unfollow_hides_company_from_radar`

## Integration

- `test_migrate_fresh_includes_0007` (ledger 7)
- `test_radar_lists_only_published_followed_changes`
- `test_user_cannot_read_another_users_watches`
- `test_delete_account_removes_watches_keeps_publications`
- `test_persist_follow_round_trip`

## E2E

- Anonymous Watch on Signal → magic link → company is watched → `/radar` shows `PUBLISHED_FIXTURE_HEADLINE` and not `UNPUBLISHED_FIXTURE_HEADLINE`.
- Unfollow → `/radar` empty or without that headline.
- `/radar` without a session redirects to login.

## Security

- Cross-user isolation on GET/POST/DELETE.
- No email as a foreign key.
- No secrets in product_events or logs.
