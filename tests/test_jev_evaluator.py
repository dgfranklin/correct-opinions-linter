import asyncio
from types import SimpleNamespace

import pytest

from evaluators.evaluator import EvaluationResult, TokenUsage
from evaluators.factory import create_evaluator
from evaluators.gemini_evaluator import GeminiOpinionEvaluator
from evaluators.jev_evaluator import JevOpinionEvaluator


class FakeTypeSafeClient:
    def __init__(self, scores, usage=None):
        self.scores = scores
        self.usage = usage
        self.request = None

    async def system_one(self, **kwargs):
        self.request = kwargs
        answers = {
            question_id: SimpleNamespace(noul=self.scores[question_id])
            for question_id in kwargs["questions"]
        }
        return SimpleNamespace(answers=answers, usage=self.usage)


def test_jev_evaluator_batches_opinions_and_thresholds_probabilities():
    client = FakeTypeSafeClient(
        {
            "opinion_2": 0.91,
            "opinion_7": 0.12,
            "opinion_15": 0.74,
            "opinion_39": 0.51,
        },
        usage=SimpleNamespace(input_tokens=321, output_tokens=40),
    )
    evaluator = JevOpinionEvaluator(
        api_key="test-key",
        model="jev-test",
        threshold=0.5,
        client=client,
    )

    result = asyncio.run(
        evaluator.evaluate(
            "I love sparkling water and driving my car.",
            {
                2: "Water should not be fizzy",
                7: "Sweet potato fries are bad",
                15: "Measuring cups are unnecessary",
                39: "Cars are bad",
            },
        )
    )

    assert result == EvaluationResult(
        violation=True,
        opinion_ids=(2, 15, 39),
        reason="#2=0.910, #15=0.740, #39=0.510",
        opinion_scores={2: 0.91, 7: 0.12, 15: 0.74, 39: 0.51},
        usage=TokenUsage(input_tokens=321, output_tokens=40),
    )
    assert client.request["model"] == "jev-test"
    assert client.request["state"] == {
        "message": "I love sparkling water and driving my car."
    }
    assert set(client.request["questions"]) == {
        "opinion_2",
        "opinion_7",
        "opinion_15",
        "opinion_39",
    }


def test_jev_evaluator_returns_probabilities_without_a_violation():
    client = FakeTypeSafeClient({"opinion_2": 0.2})
    evaluator = JevOpinionEvaluator(api_key="test-key", client=client)

    result = asyncio.run(evaluator.evaluate("Plain water is great.", {2: "No fizzy water"}))

    assert result == EvaluationResult(
        violation=False,
        opinion_scores={2: 0.2},
    )


def test_jev_evaluator_validates_threshold():
    with pytest.raises(ValueError, match="between 0 and 1"):
        JevOpinionEvaluator(api_key="test-key", threshold=1.1)


def test_evaluator_factory_rejects_missing_selected_provider_key():
    with pytest.raises(RuntimeError, match="TypeSafe API key"):
        create_evaluator("jev", gemini_api_key="unused")


def test_evaluator_factory_can_select_either_provider():
    jev = create_evaluator("jev", jev_api_key="test-key")
    gemini = create_evaluator("gemini", gemini_api_key="test-key")

    assert isinstance(jev, JevOpinionEvaluator)
    assert isinstance(gemini, GeminiOpinionEvaluator)


def test_evaluator_factory_rejects_unknown_provider():
    with pytest.raises(ValueError, match="Unsupported opinion evaluator"):
        create_evaluator("unknown", gemini_api_key="unused")
