# agent-issue-10-consumer-auth — Test Contract

Issue: https://github.com/Atharva-Kanherkar/privacyradar/issues/10
Parent epic: https://github.com/Atharva-Kanherkar/privacyradar/issues/2
Depends on: #9 (merged PR #23 / `f8896c8`)
Base: `main` at `f8896c8`

This contract is locked before implementation. If requirements change, update and commit this file separately before changing code.

## Outcome

Consumers can create a session with an email magic link, choose an explicit policy region, export their account, and delete it. Browsing, search, and evidence stay public. No organizations, SSO, social login, or billing.

## Non-goals

- Watchlists / My Radar persistence (#11). Auth may keep a `callbackURL` / `next` path so a later Watch can resume.
- Notification delivery (#12). Do not send change alerts.
- Live Resend in CI. Magic links use a fixture inbox table when `AUTH_DELIVERY=fixture`.
- Google/Apple OAuth.
- Paid checkout (#16). #3 stays open.

## Provider ADR

`docs/adr/0001-better-auth.md`: Better Auth on the existing Postgres database. Tokens are hashed and single-use. Expiry 10 minutes. Request cooldown. Responses do not reveal whether the email exists.

## Invariants

1. `/`, `/companies`, `/companies/[slug]`, `/changes`, `/methodology`, `/feed.xml` require no cookie.
2. Session identity comes only from a validated Better Auth session cookie. Never from a JSON `userId`.
3. Magic-link URLs, raw tokens, emails, and `AUTH_SECRET` never appear in logs or `publish-stats`.
4. Region is stored on `consumer_profiles.region` and is never inferred from IP.
5. Account deletion removes/anonymizes personal rows (profile, sessions, accounts, inbox). Publication revisions and change events stay.
6. Open redirects: `callbackURL` must be a same-origin relative path starting with `/`.
7. Enumeration: requesting a link for an unknown email returns the same public copy as a known email.

## Schema (migration `0006`)

Additive. Ledger **6**.

Better Auth tables (snake_case): `auth_users`, `auth_sessions`, `auth_accounts`, `auth_verifications`.

App tables:

- `consumer_profiles(user_id pk, region text not null, created_at, updated_at)` region in (`US`,`EU`,`UK`,`other`,`unspecified`)
- `consent_events` append-only (`id, user_id, action, created_at`) action in (`signup`,`region_change`,`export`,`delete_requested`,`deleted`)
- `auth_magic_inbox(id, email_hash, url, created_at)` used only when `AUTH_DELIVERY=fixture`; CI and Playwright read it. Production delivery adapter must not write here.

`db/schema.sql` includes these objects.

## Functional behavior

- `GET /login` — email form. Generic success: “If that address can be used, we sent a link.”
- `POST /api/auth/*` — Better Auth handler.
- Fixture delivery stores the link keyed by `sha256(email)`. Playwright signs in by opening that URL.
- After first session, if profile region is `unspecified`, `/account` prompts for a region before other settings.
- `/account` — region select, session sign-out, export JSON, delete with typed confirmation `DELETE`.
- `GET /account/export` — JSON of profile + consent events + session metadata (no raw tokens).
- `POST /account/delete` — idempotent; subsequent requests 401 or “already deleted”.
- Header: `Sign in` when anonymous; `Account` when signed in. Public pages unchanged.

Passkeys: Better Auth passkey plugin is wired on `/account` for later browsers. This issue’s required e2e path is magic link. A virtual-authenticator passkey test is optional, not a merge blocker.

## Unit Tests

- `test_callback_url_rejects_absolute_and_protocol_relative`
- `test_magic_link_request_does_not_reveal_account`
- `test_email_hash_not_equal_to_email`

## Integration

- `test_migrate_fresh_includes_0006` (ledger 6)
- `test_delete_account_removes_profile_keeps_publications`
- `test_fixture_inbox_stores_link_not_plaintext_token_in_logs`

## E2E

- Anonymous home/catalog still work.
- Login → fixture inbox link → `/account` → set region US → export JSON contains region.
- Delete account → subsequent `/account` redirects to login.
- Replay of the same magic-link URL does not create a second session (401/invalid).
- Open redirect: `/api/auth/magic-link/verify?...&callbackURL=https://evil.test` does not leave the origin.

## Security

- `AUTH_SECRET` is required in production; CI uses a documented test secret in the workflow env, not a repo file.
- No `AUTH_SECRET` in client bundles (`next build` grep of `.next/static` optional smoke).
