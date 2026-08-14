# Notification gates

Issue: https://github.com/Atharva-Kanherkar/privacyradar/issues/12

| Gate | Threshold | Rollback |
|---|---|---|
| Provider in publication txn | forbidden | Publication still commits; fan-out job only |
| Unpublished / non-material events | no fan-out, no mail | Existing published pages stay readable |
| Duplicate alert | unique `(user_id, event_id, channel, revision)` | Retry is a no-op |
| `product_switches.notifications = false` | skip new jobs and send | Outbox stays; no provider calls |
| Live Resend in CI | forbidden | `NOTIFY_PROVIDER=fake` (default) |
| Bounce / complaint | suppress by `email_hash` | Operator reviews; do not keep mailing |
| Tracking pixels | forbidden | Plain text + HTML without images |

`privacyradar notify-stats` prints pending/sent/suppressed/failed and lag without emails or tokens.

Corrections enqueue `kind=correction` / revision `2` for recipients who already received revision `1`. Unsubscribe still wins before send.
