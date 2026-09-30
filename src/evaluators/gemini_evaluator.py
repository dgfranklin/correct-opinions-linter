"""Gemini implementation of the opinion evaluator interface."""

import json
from dataclasses import replace
from typing import Any

from google import genai

from evaluators.evaluator import EvaluationResult, TokenUsage

SYSTEM_PROMPT_TEMPLATE = """\
You are an opinion-violation detector. You will be given a message and a numbered \
list of "correct opinions." Your job is to determine whether the message \
**contradicts or violates** any of the correct opinions.

Rules:
- A violation means the user's message expresses a view that is clearly the \
OPPOSITE of or CONTRADICTS one of the correct opinions.
- The message must have a clear, substantive connection to the opinion — not \
just mention the same topic. For example, merely mentioning "water" does not \
violate opinion #2 unless the user says something like "I love sparkling water" \
or "water should taste like something."
- If the message is ambiguous, short, or off-topic, respond with NO violation.
- Only flag clear, obvious violations. When in doubt, do NOT flag.
- A message can violate at most 3 opinions. Pick the strongest matches.

Correct Opinions:
{opinions_text}

Respond ONLY with valid JSON in one of these formats:

If there IS a violation:
{{"violation": true, "opinions": [<number>, ...], "reason": "<brief explanation>"}}

If there is NO violation:
{{"violation": false}}

Do NOT include any other text outside the JSON.
"""


class EvaluationError(RuntimeError):
    """Raised when a model cannot produce a valid evaluation."""


def build_opinions_text(opinions: dict[int, str]) -> str:
    """Format opinions as a numbered list for a model prompt."""
    return "\n".join(f"  #{number}: {text}" for number, text in opinions.items())


def parse_evaluation_response(raw: str, opinions: dict[int, str]) -> EvaluationResult:
    """Parse and validate a model response into the common result type."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        cleaned = cleaned.removesuffix("```").strip()

    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as error:
        raise EvaluationError(f"Model returned invalid JSON: {cleaned}") from error

    if not isinstance(payload, dict) or not isinstance(payload.get("violation"), bool):
        raise EvaluationError("Model response must contain a boolean 'violation' field")

    if not payload["violation"]:
        return EvaluationResult(violation=False)

    raw_ids = payload.get("opinions")
    if not isinstance(raw_ids, list):
        raise EvaluationError("Violation response must contain an 'opinions' list")

    opinion_ids = tuple(
        dict.fromkeys(
            opinion_id
            for opinion_id in raw_ids
            if isinstance(opinion_id, int) and opinion_id in opinions
        )
    )
    if not opinion_ids:
        raise EvaluationError("Violation response did not reference a known opinion")

    reason = payload.get("reason")
    return EvaluationResult(
        violation=True,
        opinion_ids=opinion_ids[:3],
        reason=reason if isinstance(reason, str) else None,
    )


class GeminiOpinionEvaluator:
    """Evaluate opinion violations using a Gemini text model."""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-3.8-flash",
        client: Any | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("Gemini API key is required")
        self.model = model
        self._client = client or genai.Client(api_key=api_key)

    @property
    def name(self) -> str:
        return f"gemini:{self.model}"

    async def evaluate(
        self, message: str, opinions: dict[int, str]
    ) -> EvaluationResult:
        if not message or len(message.strip()) < 3:
            return EvaluationResult(violation=False)

        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            opinions_text=build_opinions_text(opinions)
        )
        response = await self._client.aio.models.generate_content(
            model=self.model,
            contents=f'{system_prompt}\n\nMessage: """{message}"""',
            config=genai.types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=1024,
                response_mime_type="application/json",
                response_json_schema={
                    "type": "object",
                    "properties": {
                        "violation": {"type": "boolean"},
                        "opinions": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "maxItems": 3,
                        },
                        "reason": {"type": "string"},
                    },
                    "required": ["violation"],
                },
                thinking_config=genai.types.ThinkingConfig(
                    thinking_level=genai.types.ThinkingLevel.LOW
                ),
                automatic_function_calling=genai.types.AutomaticFunctionCallingConfig(
                    disable=True,
                ),
            ),
        )

        if not response.text:
            raise EvaluationError("Model returned an empty response")

        result = parse_evaluation_response(response.text, opinions)
        metadata = response.usage_metadata
        usage = None
        if metadata is not None:
            output_parts = (
                metadata.candidates_token_count,
                metadata.thoughts_token_count,
            )
            output_tokens = (
                sum(count or 0 for count in output_parts)
                if any(count is not None for count in output_parts)
                else None
            )
            usage = TokenUsage(
                input_tokens=metadata.prompt_token_count,
                output_tokens=output_tokens,
            )
        return replace(result, usage=usage)
