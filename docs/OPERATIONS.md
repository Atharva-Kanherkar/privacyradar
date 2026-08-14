# Operations

PrivacyRadar free-core runbook. This is not a launch approval.

## Environments

| Name | Role |
|---|---|
| Local | Developer Postgres + Next.js + worker CLI |
| CI | Ephemeral Postgres; `NOTIFY_PROVIDER=fake`; `AUTH_DELIVERY=fixture`; assistant off |
| Production | Owner-managed. Secrets stay in the host environment, never in GitHub Actions `secrets.*` interpolation |

## Migrate

Forward-only. From a clean checkout:

```bash
privacyradar migrate
privacyradar seed-fixtures   # local/CI only
```

Do not down-migrate. Rollback is kill switches plus a restore from backup.

## Backup and restore

Target RPO: 24 hours. Target RTO: 4 hours. These are **targets**, not a completed production drill.

1. `pg_dump -Fc` the application database daily. Store off-host.
2. Restore into a scratch database: `pg_restore --clean --if-exists`.
3. Run `privacyradar migrate` (should report already at head).
4. Confirm `GET /api/health` is `{"status":"ok","database":"connected"}` and a company page still shows published quotes.
5. Record the drill date. Until a production drill is recorded, treat restore as unproven.

## Kill switches

```sql
update product_switches set enabled = false, updated_at = now() where key = 'publication';
update product_switches set enabled = false, updated_at = now() where key = 'notifications';
update product_switches set enabled = false, updated_at = now() where key = 'assistant';
```

| Switch | Default | Off behavior |
|---|---|---|
| `publication` | true | Refuses new publish/rollback. Existing pages stay |
| `notifications` | true | Skips new fan-out and send. Outbox remains |
| `assistant` | **false** | No answers. Company pages stay |

Cohort expansion: `update catalog_cohorts set enabled = false where key = 'c1';`

## Provider outage

- Fetch: last verified snapshot stays; health becomes check delayed. Never hash empty bodies.
- Notify: `NOTIFY_PROVIDER=fake` locally. Live Resend is optional and unused in CI. Bounces suppress by email hash.
- Assistant: keep the switch off. Do not fail over to an arbitrary model.

## Queue backlog

`privacyradar fetch-stats` and `privacyradar notify-stats`. If leases pile up, scale workers; do not disable uniqueness constraints.

## On-call checks

1. `/api/health`
2. A known company page still quotes published evidence
3. Kill switches as intended (`assistant` false)
4. No secrets in application logs
