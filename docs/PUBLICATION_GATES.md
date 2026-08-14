# Publication and materiality gates

Issue: https://github.com/Atharva-Kanherkar/privacyradar/issues/8

| Gate | Threshold | Rollback |
|---|---|---|
| Invalid/missing quote | cannot publish | Keep last published revision |
| Materiality heuristic precision | ≥ 0.95 on 200 synthetic pairs | Keep `review_pending`; do not auto-publish |
| Auto-publish | off | Operator `publish-run` only |
| `product_switches.publication` | feature off refuses new publishes | Existing revisions stay readable |

`privacyradar eval-materiality` and `pytest tests/test_materiality_eval.py` fail the build when a gate is missed. Live OpenAI is not used.

Public home and RSS list `publication_state = 'published'` only. Company change history also includes `corrected` replacements.
