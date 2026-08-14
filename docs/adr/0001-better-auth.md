# ADR 0001 — Consumer authentication with Better Auth

Status: accepted for issue #10
Date: 2026-08-14

## Decision

Use [Better Auth](https://www.better-auth.com/) on the existing PostgreSQL database for passwordless consumer sessions.

## Why

The product plan already selected Better Auth with hashed, single-use magic-link tokens, 10-minute expiry, and generic responses. A maintained library beats a custom token table for cookie sessions, CSRF, and passkey plugins. Hosting auth at a third-party IdP would add a subprocessor before the concierge pilot (#3) has run.

## Consequences

- Schema is owned by numbered SQL migrations (`0006`), not a silent Better Auth CLI in production.
- Email delivery is an adapter: fixture inbox in CI, Resend-compatible later (#12).
- No Google/Apple login until conversion data demands it.
- Watchlists stay in #11; this ADR only authenticates a consumer and stores region/consent.
