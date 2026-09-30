import asyncio
from types import SimpleNamespace

import pytest

from evaluators.evaluator import EvaluationResult, OpinionEvaluator, TokenUsage
from evaluators.gemini_evaluator import (
    EvaluationError,
    GeminiOpinionEvaluator,
    build_opinions_text,
    parse_evaluation_response,
)

OPINIONS = {2: "Water should not be fizzy", 7: "Sweet potato fries are bad"}


def test_build_opinions_text_formats_numbered_lines():
    assert build_opinions_text(OPINIONS) == (
        "  #2: Water should not be fizzy\n  #7: Sweet potato fries are bad"
    )


def test_parse_violation_response_normalizes_known_opinions():
    result = parse_evaluation_response(
        '```json\n{"violation": true, "opinions": [7, 999, 7], "reason": "contradiction"}\n```',
        OPINIONS,
    )

    assert result == EvaluationResult(
        violation=True, opinion_ids=(7,), reason="contradiction"
    )


def test_parse_non_violation_response():
    assert parse_evaluation_response('{"violation": false}', OPINIONS) == EvaluationResult(
        violation=False
    )


def test_parse_response_rejects_unknown_opinions():
    with pytest.raises(EvaluationError, match="known opinion"):
        parse_evaluation_response('{"violation": true, "opinions": [999]}', OPINIONS)


def test_fake_evaluator_satisfies_common_interface():
    class FakeEvaluator:
        name = "fake:test"

        async def evaluate(self, message, opinions):
            return EvaluationResult(violation=False)

    evaluator: OpinionEvaluator = FakeEvaluator()

    assert evaluator.name == "fake:test"


def test_gemini_evaluator_records_billable_output_and_input_tokens():
    class FakeModels:
        async def generate_content(self, **kwargs):
            return SimpleNamespace(
                text='{"violation": false}',
                usage_metadata=SimpleNamespace(
                    prompt_token_count=1_200,
                    candidates_token_count=18,
                    thoughts_token_count=42,
                ),
            )

    client = SimpleNamespace(aio=SimpleNamespace(models=FakeModels()))
    evaluator = GeminiOpinionEvaluator(api_key="test-key", client=client)

    result = asyncio.run(evaluator.evaluate("Plain water is great.", OPINIONS))

    assert result == EvaluationResult(
        violation=False,
        usage=TokenUsage(input_tokens=1_200, output_tokens=60),
    )
