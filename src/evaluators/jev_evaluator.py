"""TypeSafe Jev implementation of the opinion evaluator interface."""

from typing import Any

from typesafe_sdk import AsyncTypeSafeClient, Noul, NoulCriteria

from evaluators.evaluator import EvaluationResult, TokenUsage

QUESTION = "Does `message` clearly express or imply a view that contradicts `correct_opinion`?"

CRITERIA = NoulCriteria(
    true=(
        "The message clearly endorses the opposite of the correct opinion, including through "
        "a preference, habit, purchase, plan, praise, or criticism that implies disagreement."
    ),
    false=(
        "The message agrees with the correct opinion, only mentions the topic, states an "
        "unrelated fact, or is too ambiguous to establish disagreement."
    ),
)


class JevOpinionEvaluator:
    """Evaluate every opinion as a parallel TypeSafe Noul question."""

    def __init__(
        self,
        api_key: str,
        model: str = "jev-latest",
        threshold: float = 0.5,
        client: Any | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("TypeSafe API key is required")
        if not 0 <= threshold <= 1:
            raise ValueError("Jev threshold must be between 0 and 1")

        self.model = model
        self.threshold = threshold
        self._client = client or AsyncTypeSafeClient(api_key=api_key)

    @property
    def name(self) -> str:
        return f"jev:{self.model}@{self.threshold:g}"

    async def evaluate(
        self, message: str, opinions: dict[int, str]
    ) -> EvaluationResult:
        if not message or len(message.strip()) < 3:
            return EvaluationResult(violation=False)
        if not opinions:
            return EvaluationResult(violation=False)

        question_ids = {
            f"opinion_{opinion_id}": opinion_id for opinion_id in opinions
        }
        questions = {
            question_id: Noul(
                instructions={
                    "correct_opinion": opinions[opinion_id],
                    "question": QUESTION,
                },
                criteria=CRITERIA,
            )
            for question_id, opinion_id in question_ids.items()
        }
        response = await self._client.system_one(
            model=self.model,
            state={"message": message},
            questions=questions,
        )

        scores = {
            opinion_id: response.answers[question_id].noul
            for question_id, opinion_id in question_ids.items()
        }
        matches = sorted(
            (
                (opinion_id, probability)
                for opinion_id, probability in scores.items()
                if probability >= self.threshold
            ),
            key=lambda item: item[1],
            reverse=True,
        )[:3]
        opinion_ids = tuple(opinion_id for opinion_id, _ in matches)

        reason = None
        if matches:
            reason = ", ".join(
                f"#{opinion_id}={probability:.3f}"
                for opinion_id, probability in matches
            )

        response_usage = getattr(response, "usage", None)
        usage = None
        if response_usage is not None:
            usage = TokenUsage(
                input_tokens=response_usage.input_tokens,
                output_tokens=response_usage.output_tokens,
            )

        return EvaluationResult(
            violation=bool(opinion_ids),
            opinion_ids=opinion_ids,
            reason=reason,
            opinion_scores=scores,
            usage=usage,
        )
