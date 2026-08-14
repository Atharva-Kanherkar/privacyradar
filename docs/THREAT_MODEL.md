# Auth threat model (issue #10)

This is the consumer-auth slice only. Publication, fetch, and billing threats stay in their issues.

## Assets

- Session cookie (Better Auth, httpOnly)
- Magic-link token (hashed at rest, 10-minute expiry, single use)
- Email address, chosen policy region, consent audit
- `AUTH_SECRET`

## Actors

- Anonymous visitor (public browse)
- Signed-in consumer
- Attacker with a leaked or guessed magic-link URL
- Attacker who can submit cross-site forms

## Controls

| Threat | Control |
|---|---|
| Account enumeration | Same public copy and JSON body whether the email is new or known |
| Open redirect | `callbackURL` must be a same-origin path starting with `/`; verify handler rewrites anything else to `/account` |
| Token replay | Hashed stored token; first verify consumes it |
| Session fixation | New session minted only after consume; cookie set by Better Auth |
| CSRF on sign-in | Origin / Fetch Metadata checks in Better Auth |
| Brute force | Magic-link rate limit (20 / 60s) plus generic cooldown |
| Secret leakage | `AUTH_SECRET` is env-only; logger disabled; client-bundle grep in CI |
| PII in logs | Auth logger disabled; publish-stats has no emails or tokens |
| IDOR | Mutations use `auth.api.getSession` from the cookie, never a JSON `userId` |
| Region inference | Region is stored only from an explicit form on `/account` |
| Residual PII after delete | `privacyradar_delete_consumer` drops profile, sessions, accounts, inbox, and user; consent rows remain as an audit without email |
| Fixture inbox in production | Inbox writes and `/api/test/magic-inbox` require `AUTH_DELIVERY=fixture` |

Passkeys are not a merge-required control in this issue. Magic link is the required path.

## Closeout (issue #17)

This section records residual product risks. It does **not** certify the system as threat-free or launch-ready.

| Area | Residual risk | Current control |
|---|---|---|
| Fetch | SSRF via catalog or future operator URLs | Catalog URLs classified; nominations are not fetched |
| Publication | Model-invented quotes | Quote-anchor validator; unpublished candidates never public |
| Notifications | Duplicate or live send in CI | Unique outbox; `NOTIFY_PROVIDER=fake`; HMAC unsubscribe |
| Compare | Unknown cells read as favorable | Copy: not found in evidence; no overall score |
| Assistant | Prompt injection / uncited answers | Switch off; no citation ⇒ refuse; fake provider in CI |
| Catalog | Vanity count of broken URLs | `c1` disabled; health gate=stop |
| Billing | Accidental paid checkout | #16 not implemented; keep checkout disabled |
| Pilot | Fake study participants | #3 stays open |

Owner actions still required: production restore drill, required-check additions, #3, #16 approval, assistant eval on live routing.

