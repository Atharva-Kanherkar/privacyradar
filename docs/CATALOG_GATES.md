# Catalog expansion gates

Issue: https://github.com/Atharva-Kanherkar/privacyradar/issues/13

Catalog size is not success. A company counts only when it has canonical identity, an official privacy URL, an explicit region, and a healthy source.

| Gate | Threshold | Current decision |
|---|---|---|
| Scheduled-fetch success | ≥95% of enabled sources `healthy` | Not claimed |
| Evidence-validation pass rate | ≥98% `exact` spans | Not claimed |
| Duration | two recorded `catalog_health_snapshots` | `gate=stop` until then |
| Publication review | unchanged | Never bypassed to hit a count |

`privacyradar catalog-health` prints `gate=stop` or `gate=advance`. Cohort `c1` stays disabled in `catalog_cohorts` until advance. The YAML may list future official URLs; they are not seeded as crawl targets while disabled.

**Stop:** PrivacyRadar does not claim 500 healthy companies. The monitored set is the enabled `seed` cohort (10 hand-picked properties) until two measured cycles pass. Nominations are requested, not monitored.

Rollback: set `catalog_cohorts.enabled = false` for a cohort. Do not down-migrate.
