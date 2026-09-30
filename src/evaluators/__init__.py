"""Swappable model evaluators for correct-opinion violations."""

from evaluators.evaluator import EvaluationResult, OpinionEvaluator, TokenUsage
from evaluators.factory import SUPPORTED_PROVIDERS, create_evaluator
from evaluators.gemini_evaluator import GeminiOpinionEvaluator
from evaluators.jev_evaluator import JevOpinionEvaluator

__all__ = [
    "EvaluationResult",
    "GeminiOpinionEvaluator",
    "JevOpinionEvaluator",
    "OpinionEvaluator",
    "SUPPORTED_PROVIDERS",
    "TokenUsage",
    "create_evaluator",
]
