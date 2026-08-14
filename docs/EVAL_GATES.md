# Extraction evaluation gates

Issue: https://github.com/Atharva-Kanherkar/privacyradar/issues/7

These gates apply to the **synthetic golden corpus** in `worker/eval/golden/` with the deterministic fixture adapter. Live model scores are not a merge requirement.

| Gate | Threshold | Rollback |
|---|---|---|
| Citation validity | 1.0 | Keep prior taxonomy version; do not publish candidates (#8) |
| Unsupported-claim rate | 0.0 | Same |
| Precision / recall | ≥ 0.99 | Pin previous `TAXONOMY_VERSION` / `PROMPT_VERSION` |
| Latency (golden + fake) | < 5s | Investigate runner, not production traffic |
| Cost (golden) | 0 | CI must not call OpenAI |

`privacyradar eval-extract` and `pytest tests/test_eval.py` fail the build when a gate is missed.

Changing category/attribute lists requires a new taxonomy version string and a new `taxonomy_versions` row. Old `extraction_runs` stay.
