from pathlib import Path

from eval_runner import (
    EvalCase,
    calculate_metrics,
    load_dataset,
)
from evaluators.evaluator import EvaluationResult


def test_artificial_dataset_is_valid_and_balanced():
    opinions, cases = load_dataset(Path("evals/artificial.json"))

    assert len(opinions) == 40
    assert len(cases) == 38
    assert sum(case.expected_violation for case in cases) == 19
    observed = {case.case_id: case for case in cases if case.source.startswith("observed_")}
    assert len(observed) == 10
    assert observed["observed-baking-precision"].expected_opinion_ids == (15,)
    assert observed["observed-spinach-agreement"].expected_violation is False


def test_calculate_metrics_counts_classification_and_opinion_matches():
    cases = [
        EvalCase("tp", "bad", True, (2,)),
        EvalCase("fn", "missed", True, (7,)),
        EvalCase("tn", "fine", False, ()),
        EvalCase("fp", "fine", False, ()),
        EvalCase("error", "error", False, ()),
    ]
    results = [
        EvaluationResult(True, (2,)),
        EvaluationResult(False),
        EvaluationResult(False),
        EvaluationResult(True, (7,)),
        None,
    ]

    metrics = calculate_metrics(cases, results)

    assert metrics.completed == 4
    assert metrics.errors == 1
    assert metrics.coverage == 0.8
    assert metrics.true_positives == 1
    assert metrics.true_negatives == 1
    assert metrics.false_positives == 1
    assert metrics.false_negatives == 1
    assert metrics.accuracy == 0.5
    assert metrics.overall_success_rate == 0.4
    assert metrics.precision == 0.5
    assert metrics.recall == 0.5
    assert metrics.f1 == 0.5
    assert metrics.opinion_accuracy == 0.5
