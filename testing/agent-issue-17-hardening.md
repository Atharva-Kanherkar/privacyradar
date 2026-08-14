# agent-issue-17-hardening — Test Contract

Issue: https://github.com/Atharva-Kanherkar/privacyradar/issues/17
Parent epic: https://github.com/Atharva-Kanherkar/privacyradar/issues/2
Depends on: #4–#15 (merged). Base: `main` at `0b0779a`.

This contract is locked before implementation. If requirements change, update and commit this file separately before changing code.

## Outcome

Document how the assembled free core is operated, recovered, and shut off. Record remaining launch gates honestly. **Do not claim launch-ready.**

## Non-goals

- Enabling paid checkout (#16)
- Closing the 30-user pilot (#3)
- Enabling the assistant switch
- Claiming 500 healthy companies
- Weakening CI, publication, notification, or catalog gates
- A production restore drill against live customer data (document the procedure only)

## Invariants

1. `docs/LAUNCH_STATUS.md` states the product is **not launch-ready** and lists unmet gates.
2. Kill switches `publication`, `notifications`, and `assistant` remain independently togglable. `assistant` stays false.
3. The core journey browse → evidence → auth → follow → published change → one alert → unsubscribe → delete is covered by Playwright.
4. Runbooks do not include secrets. Restore notes use a documented RPO/RTO *target*, not a claimed measured drill.
5. Threat-model closeout lists residual risks; it does not mark the system as threat-free.

## Schema

None. Ledger remains **11**. Tables remain **39**.

## Functional behavior

- `docs/OPERATIONS.md` covers migrate, backup/restore, kill switches, on-call checks, and queue/provider outage notes.
- `docs/LAUNCH_STATUS.md` is the release decision record: not approved.
- `docs/THREAT_MODEL.md` adds a closeout section for fetch, publication, notify, compare, and assistant.

## Tests

- `test_kill_switches_exist_and_assistant_is_off`
- Playwright `e2e/journey.spec.ts`: home → Signal evidence → sign-in → watch → fixture publish → one fake email → unsubscribe → delete account

## Security

- No new public debug endpoints.
- Fixture publish and magic inbox remain `AUTH_DELIVERY=fixture` only.
