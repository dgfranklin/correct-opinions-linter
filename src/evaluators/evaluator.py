"""Model-independent interface for evaluating messages against opinions."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class EvaluationResult:
    """Normalized result returned by every opinion evaluator."""

    violation: bool
    opinion_ids: tuple[int, ...] = ()
    reason: str | None = None


class OpinionEvaluator(Protocol):
    """Interface implemented by swappable model-backed evaluators."""

    @property
    def name(self) -> str:
        """Human-readable evaluator and model name."""
        ...

    async def evaluate(
        self, message: str, opinions: dict[int, str]
    ) -> EvaluationResult:
        """Classify a message against a numbered opinion set."""
        ...
