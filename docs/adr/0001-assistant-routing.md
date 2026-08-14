# ADR 0001 — Assistant provider and routing

Status: accepted  
Issue: https://github.com/Atharva-Kanherkar/privacyradar/issues/15

## Decision

The consumer assistant has **no model picker**. Routing is server-controlled:

- Default and CI: `ASSISTANT_PROVIDER=fake` — deterministic answers from retrieved published quotes only.
- A live provider may be added later behind the same interface. It is not wired in this issue.
- `product_switches.assistant` is independent and defaults to **false**.

## Consequences

- CI never calls OpenAI or any network model.
- Enabling the assistant in production requires an explicit switch flip **and** a passing `eval-assistant` gate, plus owner approval.
- Changing providers is an operator config change, not a user entitlement.
