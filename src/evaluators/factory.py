"""Configuration-driven construction of opinion evaluators."""

from evaluators.evaluator import OpinionEvaluator
from evaluators.gemini_evaluator import GeminiOpinionEvaluator
from evaluators.jev_evaluator import JevOpinionEvaluator

SUPPORTED_PROVIDERS = ("gemini", "jev")


def create_evaluator(
    provider: str,
    *,
    gemini_api_key: str | None = None,
    gemini_model: str = "gemini-3.8-flash",
    jev_api_key: str | None = None,
    jev_model: str = "jev-latest",
    jev_threshold: float = 0.5,
) -> OpinionEvaluator:
    """Build the requested evaluator while validating only its required key."""
    normalized_provider = provider.strip().lower()

    if normalized_provider == "gemini":
        if not gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is required for the Gemini evaluator")
        return GeminiOpinionEvaluator(api_key=gemini_api_key, model=gemini_model)

    if normalized_provider == "jev":
        if not jev_api_key:
            raise RuntimeError(
                "A TypeSafe API key is required for the Jev evaluator; "
                "set TYPESAFE_API_KEY or JEV_API_KEY"
            )
        return JevOpinionEvaluator(
            api_key=jev_api_key,
            model=jev_model,
            threshold=jev_threshold,
        )

    supported = ", ".join(SUPPORTED_PROVIDERS)
    raise ValueError(f"Unsupported opinion evaluator '{provider}'. Choose one of: {supported}")
