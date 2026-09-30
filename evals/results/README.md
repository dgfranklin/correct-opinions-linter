# Recorded evaluation runs

## Provider comparison — 2026-09-29

See `provider-comparison-2026-09-29.md` for the matched quality, token usage, paid-list-price,
and latency comparison between Gemini 3.8 Flash and TypeSafe Jev.

Instrumented run data:

- `gemini-3.8-flash-2026-09-29-benchmark.json`
- `jev-latest-2026-09-29-benchmark.json`

## Gemini 3.8 Flash — 2026-09-29

Primary report: `gemini-3.8-flash-2026-09-29-benchmark.json`

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

## TypeSafe Jev latest — 2026-09-29

Primary report: `jev-latest-2026-09-29-benchmark.json`

The run evaluated all 38 cases with no provider errors, using a `0.5` violation threshold.

| Metric | Result |
| --- | ---: |
| Coverage | 100% (38/38) |
| Accuracy | 97.37% (37/38) |
| Precision | 100% |
| Recall | 94.74% |
| F1 | 97.30% |
| Opinion identification | 94.74% |
| False positives | 0 |
| False negatives | 1 |

False negative:

- `observed-star-wars-episode-one` — expected opinion #32

An offline sweep of the recorded opinion scores confirmed the `0.5` threshold as the safer
tradeoff for this dataset. Lowering it to `0.34` catches the remaining false negative but also
introduces three false positives.
