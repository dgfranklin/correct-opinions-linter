"""Swappable model evaluators for correct-opinion violations."""

from evaluators.evaluator import EvaluationResult, OpinionEvaluator
from evaluators.gemini_evaluator import GeminiOpinionEvaluator

__all__ = [
    "EvaluationResult",
    "GeminiOpinionEvaluator",
    "OpinionEvaluator",
]
