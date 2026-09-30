# Recorded evaluation runs

## Gemini 3.8 Flash — 2026-09-29

Primary report: `gemini-3.8-flash-2026-09-29-v2.json`

The run evaluated all 38 cases with no provider or parsing errors after increasing the model
response budget from 256 to 1,024 tokens.

| Metric | Result |
| --- | ---: |
| Coverage | 100% (38/38) |
| Accuracy | 86.84% (33/38) |
| Precision | 100% |
| Recall | 73.68% |
| F1 | 84.85% |
| Opinion identification | 73.68% |
| False positives | 0 |
| False negatives | 5 |

False negatives:

- `observed-baking-precision` — expected opinion #15
- `observed-milk-with-spicy-food` — expected opinion #22
- `observed-pickup-commute` — expected opinion #39
- `observed-chipotle-favorite` — expected opinion #40
- `observed-salad-dressing` — expected opinion #23
