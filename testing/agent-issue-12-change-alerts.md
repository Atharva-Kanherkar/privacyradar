# agent-issue-12-change-alerts — Test Contract

Issue: https://github.com/Atharva-Kanherkar/privacyradar/issues/12
Parent epic: https://github.com/Atharva-Kanherkar/privacyradar/issues/2
Depends on: #8 (publication), #10 (auth), #11 (watches, merged PR #25 / `e1a9d33`)
Base: `main` at `e1a9d33`

This contract is locked before implementation. If requirements change, update and commit this file separately before changing code.

## Outcome

Followers of a company receive **at most one** transactional email per published material change per channel. Publication—not extraction—creates the durable notification work. The provider is never called inside the publication transaction. Tests and CI use a **fake** adapter; live Resend is never invoked from CI.

## Non-goals

- Marketing or digest blast campaigns beyond a weekly digest hold
- Push / SMS channels (schema allows a later channel, ship email only)
- Billing / paid checkout (#16)
- Closing #3 or enabling paid checkout
- Tracking pixels or click identifiers in email HTML

## Invariants

1. A published `change_events` row (or a correction/rollback of one) inserts **one** `notification_fanout_jobs` row in the same transaction. It does not insert per-watcher outbox rows in that transaction.
2. Unpublished, `review_pending`, rejected, failed, or cosmetic/unknown events never create fan-out jobs and never send mail.
3. Unique `(user_id, event_id, channel, revision)` on `notification_outbox` makes retries and concurrent workers idempotent. Revision `1` is the original published alert; revision `2` is the correction/rollback follow-up.
4. Preferences are applied before writing an outbox row **and again** before send. Unfollow, unsubscribe, mute, and suppression win before send.
5. Email identity is never a foreign key. Suppressions key on `email_hash`. Outbox and preferences key on `user_id`.
6. Signed unsubscribe works without a session. Tokens are HMAC-signed, purpose-bound, expiring, and rejected when tampered. Unsubscribe is idempotent (email-client prefetch is not a vulnerability).
7. `product_switches.notifications = false` skips new fan-out jobs and skips send. Existing published pages stay readable.
8. Fake provider is the default. `NOTIFY_PROVIDER=resend` is required for the Resend adapter. CI and Playwright keep the fake adapter.
9. Account deletion removes that user’s preferences, outbox, deliveries, and fixture inbox rows. Publication history and hashed bounce/complaint suppressions stay.
10. Corrections/rollback of a published event that already fanned out enqueue a `kind=correction` job so a misleading alert is not left without a follow-up.

## Schema (migration `0008`)

Additive. Ledger **8**. Required public tables **35**.

- `notification_preferences(user_id text pk, channel text not null, frequency text not null, muted_company_ids uuid[] not null default '{}', updated_at)`
  - `channel = 'email'`
  - `frequency in ('immediate', 'digest_weekly', 'unsubscribed')`
  - Missing row means quiet default: `immediate` for **material** published changes only
- `notification_fanout_jobs(id uuid pk, event_id uuid not null references change_events, kind text not null, state text not null, cursor_user_id text, expected_count int, written_count int not null default 0, claimed_at, claimed_by, lease_expires_at, created_at)`
  - unique `(event_id, kind)`
  - `kind in ('publish', 'correction')`
  - `state in ('pending', 'running', 'done', 'failed')`
- `notification_outbox(id uuid pk, user_id text not null, event_id uuid not null references change_events, channel text not null, revision int not null, kind text not null, state text not null, attempt_count int not null default 0, next_attempt_at, claimed_at, claimed_by, lease_expires_at, created_at)`
  - unique `(user_id, event_id, channel, revision)`
  - `state in ('pending', 'claimed', 'sent', 'suppressed', 'failed', 'cancelled')`
- `notification_deliveries(id uuid pk, outbox_id uuid not null references notification_outbox, provider text not null, provider_message_id text, provider_event_id text unique, state text not null, created_at)`
  - unique `(outbox_id)` where `state = 'sent'`
  - `state in ('sent', 'delivered', 'bounced', 'complained', 'failed', 'suppressed')`
- `notification_suppressions(email_hash text pk, reason text not null, created_at)`
  - `reason in ('bounce', 'complaint', 'unsubscribe')`
- `notification_fixture_inbox(id uuid pk, email_hash text not null, subject text not null, body_text text not null, body_html text not null, created_at)`
- `product_switches` seed `notifications=true`
- `privacyradar_delete_consumer` also deletes preferences, outbox, deliveries, and fixture inbox for that user

`db/schema.sql` includes these objects.

## Functional behavior

- After `publish_event` / `publish_run` commits a **material** published event, a `kind=publish` fan-out job exists.
- `privacyradar notify-fanout` pages active watchers, writes unique outbox rows, resumes by `cursor_user_id`.
- `privacyradar notify-deliver` claims due outbox rows with a lease, re-checks eligibility, renders HTML + plain text, calls the adapter, records a `sent` delivery.
- Immediate frequency sends now. `digest_weekly` holds `next_attempt_at` until the next Monday 12:00 UTC. `unsubscribed` is not written to the outbox.
- Email subject: `Privacy change at {company}: {headline}`. Body includes the claim/headline, company, why it matters, evidence URL `/changes/{event_id}`, settings URL `/radar/settings`, and unsubscribe URL `/unsubscribe?token=`.
- HTML has no images or tracking pixels. Plain text is always present.
- `GET /radar/settings` (session required) edits frequency and shows muted companies. POST uses 303 relative redirect.
- `GET /unsubscribe?token=` confirms without login. POST applies global unsubscribe (or company mute when the token is company-scoped) and shows confirmation.
- `POST /api/notifications/webhooks/resend` verifies signature + timestamp, rejects replay of `provider_event_id`, maps bounce/complaint onto suppressions. Fixture mode accepts a documented test header instead of live Svix signatures.
- `GET /api/test/notify-inbox?email=` returns the latest fake email only when `AUTH_DELIVERY=fixture` and not in hosted production.
- `privacyradar notify-stats` prints counts (pending/sent/suppressed/failed, lag) without emails or tokens.
- `privacyradar fixture-publish-change --slug --headline` exists only as a local/CI helper when `AUTH_DELIVERY=fixture`; it publishes a material event so Playwright can exercise watch → publish → one fake email.

## Unit tests

- `test_enqueue_fanout_skips_unpublished_and_non_material`
- `test_outbox_unique_survives_crash_replay`
- `test_concurrent_fanout_does_not_duplicate_outbox`
- `test_preferences_applied_before_fanout_and_before_send`
- `test_unfollow_before_send_cancels_outbox`
- `test_signed_unsubscribe_rejects_tampering_and_expiry`
- `test_render_alert_has_html_and_text_without_images`
- `test_webhook_rejects_bad_signature_and_replay`
- `test_bounce_and_complaint_suppress_future_sends`
- `test_fake_provider_never_calls_resend`

## Integration

- `test_migrate_fresh_includes_0008` (ledger 8, 35 required tables)
- `test_publish_event_inserts_one_fanout_job_not_outbox_rows`
- `test_published_change_sends_one_eligible_email_via_fake_provider`
- `test_correction_enqueues_follow_up_revision`
- `test_notifications_switch_off_skips_send`
- `test_delete_account_removes_notification_rows_keeps_publications`
- `test_persist_notification_round_trip`

## E2E

- Sign in → Watch Signal → fixture-publish a new material headline → `notify-fanout` + `notify-deliver` → fixture inbox has **one** email containing the headline, evidence path, and unsubscribe path. Unpublished fixture headline is absent.
- Visit signed unsubscribe URL without a session → confirm → preference is `unsubscribed`. A second deliver does not add a second inbox row.
- `/radar/settings` without a session redirects to login. Signed-in save of `digest_weekly` round-trips.
- Tampered token shows an invalid-link state, not a 500.

## Security

- No provider call in the publication transaction.
- No live Resend in CI.
- No email as a foreign key.
- Tokens and magic URLs never written to product_events or worker logs.
- Webhook replay and signature failures return 4xx.
- Fixture inbox and fixture-publish are disabled when `VERCEL_ENV=production` or Railway production.
