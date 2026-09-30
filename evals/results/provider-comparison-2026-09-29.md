# Gemini 3.8 Flash vs. TypeSafe Jev

Benchmark date: September 29, 2026

## Executive summary

On this repository's 38-message evaluation set, Jev was the stronger production choice:

- Accuracy was **97.37% for Jev** and **86.84% for Gemini**.
- Both providers had **100% precision** and no false positives, but Jev reduced false negatives
  from five to one.
- Mean measured API latency was **0.102 seconds for Jev** and **2.003 seconds for Gemini**.
- At current paid list prices, the measured 38 requests cost an estimated **$0.00834 with Jev**
  and **$0.03790 with Gemini**. Jev was approximately **78.0% less expensive**.

These results favor Jev for this narrow, structured classification task. They do not establish
that Jev is generally more capable than Gemini: the dataset is small, domain-specific, and built
around the exact behavior this bot needs.

## Method

Both providers evaluated the same 38 messages against the same snapshot of 40 correct opinions.
The runs were sequential and completed without provider errors:

- Gemini: `gemini-3.8-flash`, low thinking level, structured JSON response
- Jev: `jev-latest`, 40 parallel Noul questions, `0.5` violation threshold
- Dataset: `evals/artificial.json`
- Gemini run: `gemini-3.8-flash-2026-09-29-benchmark.json`
- Jev run: `jev-latest-2026-09-29-benchmark.json`

Token counts came from each provider's response metadata. Latency was measured with a monotonic
clock around each API request. Gemini's 4.1-second rate-limit delay happened outside the measured
request interval and is therefore excluded from its latency figures.

## Evaluation quality

| Metric | Gemini 3.8 Flash | TypeSafe Jev | Jev difference |
| --- | ---: | ---: | ---: |
| Accuracy | 86.84% (33/38) | 97.37% (37/38) | +10.53 pp |
| Precision | 100.00% | 100.00% | 0.00 pp |
| Recall | 73.68% | 94.74% | +21.05 pp |
| F1 | 84.85% | 97.30% | +12.45 pp |
| True positives | 14 | 18 | +4 |
| True negatives | 19 | 19 | 0 |
| False positives | 0 | 0 | 0 |
| False negatives | 5 | 1 | -4 |

Both providers passed all 28 synthetic cases. The observed-in-practice cases created the
difference: Gemini passed 5/10, while Jev passed 9/10.

Gemini false negatives:

- `observed-baking-precision`
- `observed-milk-with-spicy-food`
- `observed-pickup-commute`
- `observed-chipotle-favorite`
- `observed-salad-dressing`

Jev false negative:

- `observed-star-wars-episode-one`

The providers' failures were complementary: Gemini caught the Star Wars case that Jev missed,
while Jev caught all five observed cases that Gemini missed.

## Token usage

| Usage | Gemini 3.8 Flash | TypeSafe Jev | Jev / Gemini |
| --- | ---: | ---: | ---: |
| Total input tokens | 30,303 | 198,610 | 6.55x |
| Mean input tokens/request | 797.4 | 5,226.6 | 6.55x |
| Total output tokens | 4,045 | 30,210 | 7.47x |
| Mean output tokens/request | 106.4 | 795.0 | 7.47x |
| Requests reporting usage | 38/38 | 38/38 | — |

Jev reports substantially more tokens because this implementation asks 40 independent,
fully-specified Noul questions in one request. Its output count was exactly 795 tokens for every
case because every request returned the same 40-answer shape. Gemini sends the opinion list once
and generates one small JSON decision; its billed output includes both response and thinking
tokens.

Token counts are not directly interchangeable between providers because tokenizers and billing
semantics differ. They are useful when combined with each provider's own price, not as a
provider-independent measure of computational work.

## Pricing and estimated cost

Prices checked September 29, 2026:

- Gemini 3.8 Flash standard API: **$0.75 per million input tokens** and **$3.75 per million output
  tokens**, including thinking tokens, through December 31, 2026. Google says these rates become
  $1.50 and $7.50 on January 1, 2027. Source: [Gemini Developer API pricing](https://ai.google.dev/gemini-api/docs/pricing).
- TypeSafe Jev: **$0.042 per million input tokens** and **free output tokens**. Sources:
  [TypeSafe pricing](https://typesafe.ai/) and
  [Jev launch details](https://typesafe.ai/blog/introducing-system-one-models-and-jev).

Current paid-list-price calculation:

| Cost | Gemini 3.8 Flash | TypeSafe Jev |
| --- | ---: | ---: |
| Input for 38 requests | $0.02273 | $0.00834 |
| Output for 38 requests | $0.01517 | $0.00000 |
| Total for 38 requests | **$0.03790** | **$0.00834** |
| Mean per message | $0.000997 | $0.000220 |
| Projected 100,000 messages | $99.73 | $21.95 |
| Projected 1,000,000 messages | $997.26 | $219.52 |

At these rates and measured token volumes, Gemini costs **4.54x as much**, or Jev costs **78.0%
less**. If Google's announced January 1, 2027 rates apply and usage stays identical, Gemini would
cost approximately $1,994.53 per million messages. That future comparison assumes Jev's price
does not change.

Actual invoices may differ because of free tiers, credits, volume discounts, future price
changes, caching, retries, and changes in message length or the opinion list.

## Latency

| Request latency | Gemini 3.8 Flash | TypeSafe Jev | Gemini / Jev |
| --- | ---: | ---: | ---: |
| Mean | 2.003 s | 0.102 s | 19.58x |
| Median | 1.409 s | 0.097 s | 14.51x |
| P95 | 4.544 s | 0.146 s | 31.02x |
| Minimum | 0.853 s | 0.074 s | — |
| Maximum | 9.277 s | 0.198 s | — |
| Sum of measured API time | 76.116 s | 3.888 s | 19.58x |

Jev's advantage is consistent across the distribution, not driven by one Gemini outlier. Even
Jev's slowest request in this run was faster than Gemini's fastest request.

These are single-run, client-observed measurements from one environment. They include network
time but exclude deliberate rate-limit sleeps. They are not controlled infrastructure
benchmarks, and repeated runs are needed to characterize variance and tail latency reliably.

## Recommendation

Use Jev as the default evaluator for the bot and retain Gemini as a configurable fallback or
comparison provider. On the current workload, Jev provides:

- four additional correct classifications out of 38;
- no increase in false positives;
- materially lower interactive latency; and
- a lower estimated paid cost despite higher reported token counts.

The next useful quality step is to grow the observed-message set. The synthetic portion is
saturated at 100% for both providers and no longer distinguishes them. A larger blind set of real
Discord messages, plus repeated latency runs, would provide a more reliable basis for future
model and threshold changes.

## Reproduction

```bash
set -a; source .env.local; set +a

python src/eval_runner.py \
  --provider jev \
  --timeout 60 \
  --output evals/results/jev-latest-2026-09-29-benchmark.json

python src/eval_runner.py \
  --provider gemini \
  --timeout 60 \
  --output evals/results/gemini-3.8-flash-2026-09-29-benchmark.json
```
