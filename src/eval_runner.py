"""Run a labeled message set through an opinion evaluator and report metrics."""

import argparse
import asyncio
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from math import ceil
from pathlib import Path
from statistics import mean, median
from time import perf_counter
from typing import Any

from evaluators import (
    SUPPORTED_PROVIDERS,
    EvaluationResult,
    OpinionEvaluator,
    create_evaluator,
)

DEFAULT_DATASET = Path(__file__).resolve().parent.parent / "evals/artificial.json"


@dataclass(frozen=True)
class EvalCase:
    case_id: str
    message: str
    expected_violation: bool
    expected_opinion_ids: tuple[int, ...]
    source: str = "synthetic"


@dataclass(frozen=True)
class EvalMetrics:
    total: int
    completed: int
    errors: int
    true_positives: int
    true_negatives: int
    false_positives: int
    false_negatives: int
    opinion_matches: int
    expected_violations: int

    @property
    def coverage(self) -> float:
        return _safe_divide(self.completed, self.total)

    @property
    def accuracy(self) -> float:
        return _safe_divide(self.true_positives + self.true_negatives, self.completed)

    @property
    def overall_success_rate(self) -> float:
        return _safe_divide(self.true_positives + self.true_negatives, self.total)

    @property
    def precision(self) -> float:
        return _safe_divide(
            self.true_positives, self.true_positives + self.false_positives
        )

    @property
    def recall(self) -> float:
        return _safe_divide(
            self.true_positives, self.true_positives + self.false_negatives
        )

    @property
    def f1(self) -> float:
        return _safe_divide(2 * self.precision * self.recall, self.precision + self.recall)

    @property
    def opinion_accuracy(self) -> float:
        return _safe_divide(self.opinion_matches, self.expected_violations)


def _safe_divide(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def load_dataset(path: Path) -> tuple[dict[int, str], list[EvalCase]]:
    """Load and validate the opinion snapshot and labeled cases."""
    payload = json.loads(path.read_text())
    opinions = {int(key): value for key, value in payload["opinions"].items()}
    cases = [
        EvalCase(
            case_id=item["id"],
            message=item["message"],
            expected_violation=item["expected_violation"],
            expected_opinion_ids=tuple(item.get("expected_opinions", [])),
            source=item.get("source", "synthetic"),
        )
        for item in payload["cases"]
    ]

    if not opinions or not cases:
        raise ValueError("Dataset must contain opinions and cases")
    if len({case.case_id for case in cases}) != len(cases):
        raise ValueError("Dataset case IDs must be unique")
    for case in cases:
        if case.expected_violation and not case.expected_opinion_ids:
            raise ValueError(f"Violation case {case.case_id} needs expected opinions")
        if any(opinion_id not in opinions for opinion_id in case.expected_opinion_ids):
            raise ValueError(f"Case {case.case_id} references an unknown opinion")

    return opinions, cases


def calculate_metrics(
    cases: list[EvalCase], results: list[EvaluationResult | None]
) -> EvalMetrics:
    """Calculate binary classification and opinion-identification metrics."""
    if len(cases) != len(results):
        raise ValueError("Cases and results must have the same length")

    true_positives = true_negatives = false_positives = false_negatives = 0
    opinion_matches = expected_violations = errors = 0

    for case, result in zip(cases, results, strict=True):
        if result is None:
            errors += 1
            continue
        if case.expected_violation:
            expected_violations += 1
            if result.violation:
                true_positives += 1
                if set(case.expected_opinion_ids).issubset(result.opinion_ids):
                    opinion_matches += 1
            else:
                false_negatives += 1
        elif result.violation:
            false_positives += 1
        else:
            true_negatives += 1

    return EvalMetrics(
        total=len(cases),
        completed=len(cases) - errors,
        errors=errors,
        true_positives=true_positives,
        true_negatives=true_negatives,
        false_positives=false_positives,
        false_negatives=false_negatives,
        opinion_matches=opinion_matches,
        expected_violations=expected_violations,
    )


async def run_dataset(
    evaluator: OpinionEvaluator,
    opinions: dict[int, str],
    cases: list[EvalCase],
    delay: float = 0,
    timeout: float = 30,
) -> tuple[list[EvaluationResult | None], list[float], list[dict[str, Any]]]:
    """Evaluate cases sequentially to respect provider rate limits."""
    results: list[EvaluationResult | None] = []
    latencies: list[float] = []
    details: list[dict[str, Any]] = []

    for index, case in enumerate(cases, start=1):
        error_message = None
        started_at = perf_counter()
        try:
            result = await asyncio.wait_for(
                evaluator.evaluate(case.message, opinions), timeout=timeout
            )
        except Exception as error:
            result = None
            error_message = f"{type(error).__name__}: {error}"
        latency = perf_counter() - started_at

        results.append(result)
        latencies.append(latency)
        passed = result is not None and result.violation == case.expected_violation
        if passed and case.expected_violation:
            passed = set(case.expected_opinion_ids).issubset(result.opinion_ids)

        actual = "ERROR" if result is None else str(result.violation)
        print(
            f"[{index:02}/{len(cases):02}] {'PASS' if passed else 'FAIL'} "
            f"{case.case_id}: expected={case.expected_violation} actual={actual}",
            flush=True,
        )
        if error_message:
            print(f"    {error_message}", flush=True)
        details.append(
            {
                "id": case.case_id,
                "source": case.source,
                "message": case.message,
                "expected_violation": case.expected_violation,
                "expected_opinions": list(case.expected_opinion_ids),
                "actual": None
                if result is None
                else {
                    "violation": result.violation,
                    "opinions": list(result.opinion_ids),
                    "reason": result.reason,
                    "opinion_scores": result.opinion_scores,
                    "usage": None
                    if result.usage is None
                    else {
                        "input_tokens": result.usage.input_tokens,
                        "output_tokens": result.usage.output_tokens,
                    },
                },
                "latency_seconds": latency,
                "error": error_message,
                "passed": passed,
            }
        )

        if delay and index < len(cases):
            await asyncio.sleep(delay)

    return results, latencies, details


def performance_payload(
    results: list[EvaluationResult | None], latencies: list[float]
) -> dict[str, Any]:
    """Aggregate provider-reported tokens and measured request latency."""
    completed_latencies = [
        latency
        for result, latency in zip(results, latencies, strict=True)
        if result is not None
    ]
    sorted_latencies = sorted(completed_latencies)
    usages = [result.usage for result in results if result is not None and result.usage]
    input_counts = [usage.input_tokens for usage in usages if usage.input_tokens is not None]
    output_counts = [
        usage.output_tokens for usage in usages if usage.output_tokens is not None
    ]

    latency_summary = None
    if sorted_latencies:
        p95_index = ceil(0.95 * len(sorted_latencies)) - 1
        latency_summary = {
            "total": sum(sorted_latencies),
            "mean": mean(sorted_latencies),
            "median": median(sorted_latencies),
            "p95": sorted_latencies[p95_index],
            "min": sorted_latencies[0],
            "max": sorted_latencies[-1],
        }

    return {
        "latency_seconds": latency_summary,
        "token_usage": {
            "requests_reported": len(usages),
            "input_total": sum(input_counts),
            "output_total": sum(output_counts),
            "input_mean": mean(input_counts) if input_counts else None,
            "output_mean": mean(output_counts) if output_counts else None,
        },
    }


def metrics_payload(
    evaluator: OpinionEvaluator,
    metrics: EvalMetrics,
    results: list[EvaluationResult | None],
    latencies: list[float],
) -> dict[str, Any]:
    payload = {
        "evaluator": evaluator.name,
        "total": metrics.total,
        "completed": metrics.completed,
        "errors": metrics.errors,
        "coverage": metrics.coverage,
        "accuracy": metrics.accuracy,
        "overall_success_rate": metrics.overall_success_rate,
        "precision": metrics.precision,
        "recall": metrics.recall,
        "f1": metrics.f1,
        "opinion_accuracy": metrics.opinion_accuracy,
        "confusion_matrix": {
            "true_positives": metrics.true_positives,
            "true_negatives": metrics.true_negatives,
            "false_positives": metrics.false_positives,
            "false_negatives": metrics.false_negatives,
        },
    }
    payload.update(performance_payload(results, latencies))
    return payload


async def async_main(args: argparse.Namespace) -> int:
    opinions, cases = load_dataset(args.dataset)
    if args.case:
        requested = set(args.case)
        cases = [case for case in cases if case.case_id in requested]
        missing = requested - {case.case_id for case in cases}
        if missing:
            raise ValueError(f"Unknown case IDs: {', '.join(sorted(missing))}")
    if args.limit is not None:
        cases = cases[: args.limit]
    if not cases:
        raise ValueError("No evaluation cases selected")

    gemini_model = args.model or os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
    jev_model = args.model or os.environ.get("JEV_MODEL", "jev-latest")
    evaluator = create_evaluator(
        args.provider,
        gemini_api_key=os.environ.get("GEMINI_API_KEY"),
        gemini_model=gemini_model,
        jev_api_key=os.environ.get("TYPESAFE_API_KEY") or os.environ.get("JEV_API_KEY"),
        jev_model=jev_model,
        jev_threshold=args.threshold,
    )
    delay = args.delay
    if delay is None:
        delay = 4.1 if args.provider == "gemini" else 0
    print(f"Running {len(cases)} cases with {evaluator.name}")
    results, latencies, details = await run_dataset(
        evaluator, opinions, cases, delay, args.timeout
    )
    metrics = calculate_metrics(cases, results)
    summary = metrics_payload(evaluator, metrics, results, latencies)

    print("\nMetrics")
    print(json.dumps(summary, indent=2))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        try:
            dataset_name = str(args.dataset.relative_to(Path.cwd()))
        except ValueError:
            dataset_name = str(args.dataset)
        report = {
            "generated_at": datetime.now(UTC).isoformat(),
            "dataset": dataset_name,
            "summary": summary,
            "cases": details,
        }
        args.output.write_text(json.dumps(report, indent=2) + "\n")
        print(f"Wrote detailed results to {args.output}")

    return 1 if metrics.errors else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument(
        "--provider",
        choices=SUPPORTED_PROVIDERS,
        default=os.environ.get("OPINION_EVALUATOR", "jev"),
    )
    parser.add_argument(
        "--model",
        help="Provider model override (defaults to GEMINI_MODEL or JEV_MODEL)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=float(os.environ.get("JEV_THRESHOLD", "0.5")),
        help="Jev Noul probability threshold (default: 0.5)",
    )
    parser.add_argument(
        "--case",
        action="append",
        help="Run only this case ID; may be supplied more than once",
    )
    parser.add_argument("--limit", type=int, help="Run only the first N selected cases")
    parser.add_argument(
        "--delay",
        type=float,
        help="Seconds between requests (default: 4.1 for Gemini, 0 for Jev)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30,
        help="Maximum seconds allowed for each case (default: 30)",
    )
    parser.add_argument("--output", type=Path, help="Optional detailed JSON output path")
    return parser.parse_args()


def main() -> int:
    return asyncio.run(async_main(parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
