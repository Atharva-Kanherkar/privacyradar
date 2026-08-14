# Launch status

**Decision: not launch-ready.** Recorded with issue #17. Do not weaken a gate to close the epic.

## Met for the free core (code)

- Migrations, fixtures, CI required checks
- Immutable observations and SSRF-safe fetch
- Taxonomy + extraction eval on the golden fake corpus
- Evidence validation and publication
- Public company/change UX
- Passwordless auth and privacy controls
- Watches / My Radar
- Transactional alerts with unsubscribe (fake provider in CI)
- Catalog health gate (c1 disabled; no 500-company claim)
- Evidence-backed compare without a score
- Cited assistant **implemented and off**

## Unmet — do not launch

| Gate | Status |
|---|---|
| 30-user concierge pilot (#3) | Open. Do not fabricate participants |
| Paid checkout (#16) | Not enabled. Shadow only until #3 + owner approval |
| Catalog 500 healthy companies (#13) | Stopped at seed cohort; `gate=stop` |
| Assistant production enablement (#15) | Switch false; live-model eval not claimed |
| Production restore drill | Procedure documented; drill not recorded |
| Browser smoke + PR secret guard as required checks | Jobs exist; owner must add them |
| 10× load / SLO dashboards / on-call rota | Not claimed |

## Kill switches at this revision

`publication=true`, `notifications=true`, `assistant=false`, `catalog_cohorts.c1=false`.
