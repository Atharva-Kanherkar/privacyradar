# Assistant enablement and guardrails

The assistant is a streaming chat panel on each company page
(`web/src/components/ChatAssistant.tsx` + `POST /api/assistant`). It answers in
plain language, grounded ONLY in that company's published claims and change
events; the system prompt forbids outside knowledge and instructs verbatim
quoting.

## Gating (2026 revamp)

| Gate | Behavior |
|---|---|
| `OPENAI_API_KEY` unset | Assistant off. Company pages render a static "assistant is off" panel. CI never sets the key, so CI never calls a live model. |
| `ASSISTANT_ENABLED=false` | Kill switch. Overrides everything, assistant off. |
| `ASSISTANT_MODEL` | Optional model override (default `gpt-4.1-mini` via `OPENAI_EXTRACT_MODEL`). |
| Rate limit | 30 questions per identity per day (`assistant_usage`). Identity is the sha256 of the user id, else a platform-set client IP (`x-vercel-forwarded-for` / `x-real-ip`), else the LAST `X-Forwarded-For` hop (appended by the trusted proxy; the leftmost hop is client-forgeable). Quota is spent only after the request reaches the model, so 404s and provider failures do not burn questions. |
| Scope | Prompt-level: only the current company's published evidence; refuses other topics and says plainly when evidence is missing. |

The legacy `product_switches.assistant` row no longer gates the web assistant.
The worker's deterministic retrieval implementation and
`privacyradar eval-assistant` golden corpus remain as regression checks for the
retrieval/refusal logic.

Rollback: set `ASSISTANT_ENABLED=false` on Vercel and redeploy (or remove
`OPENAI_API_KEY` from the web environment).
