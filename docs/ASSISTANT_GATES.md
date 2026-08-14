# Assistant evaluation and enablement gates

Issue: https://github.com/Atharva-Kanherkar/privacyradar/issues/15

The cited assistant is **off by default**. Static company pages work without it.

| Gate | Threshold | Current decision |
|---|---|---|
| `product_switches.assistant` | must be false until eval + owner approval | **off** |
| Citation | every factual answer has a published claim_key | Fake provider only |
| Refusal | out-of-scope and no-evidence questions have empty citations | Enforced |
| Provider | `ASSISTANT_PROVIDER=fake` in CI | No OpenAI in CI |
| Cost | 0 in CI | Do not call a live model to merge |

`privacyradar eval-assistant` prints `gate=pass` or `gate=fail` on the golden fake corpus. Do not enable the switch because this issue merged.

Rollback: `update product_switches set enabled = false where key = 'assistant'`.
