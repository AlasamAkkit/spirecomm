"""Optional v1.7.3 strict JSON Schema for permanent card-reward evaluation.

This is a *request-format* layer, not a gameplay policy. It is deliberately
decoupled from the active v1.7.2 launcher and never edits the saved deck plan,
human teaching, checkpoints, or original LLM output.
"""
from __future__ import annotations

from typing import Any

LABEL = "CARD_REWARD_EVALUATION_V12"
FORMAT_NAME = "c2_card_reward_evaluation_v173"


def card_reward_text_format(action_count: int) -> dict[str, Any]:
    """Responses API text.format with exact numeric-string action indices.

    OpenAI's strict subset requires every object property to be required and
    additionalProperties=False. Score range (0-100) and nonempty strings are
    intentionally validated by the existing v1.7.2 controller, because the
    strict schema subset does not support every JSON Schema constraint.
    """
    if isinstance(action_count, bool) or not isinstance(action_count, int):
        raise ValueError("Expected integer action_count")
    if not 2 <= action_count <= 20:
        raise ValueError("Card reward requires 2-20 legal actions")

    string = {"type": "string"}
    string_list = {"type": "array", "items": {"type": "string"}}
    plan_fields = {
        "offense": string,
        "defense": string,
        "scaling": string,
        "draw_energy": string,
        "aoe": string,
        "weaknesses": string_list,
        "acquisition_priorities": string_list,
        "avoid": string_list,
        "add_policy": {
            "type": "string",
            "enum": ["OPEN", "SELECTIVE", "SKIP_DEFAULT"],
        },
    }
    scores = {str(index): {"type": "number"} for index in range(action_count)}
    fields = {
        "deck_plan": {
            "type": "object",
            "properties": plan_fields,
            "required": list(plan_fields),
            "additionalProperties": False,
        },
        "plan_changed": {"type": "boolean"},
        "plan_change_reason": string,
        "scores": {
            "type": "object",
            "properties": scores,
            "required": list(scores),
            "additionalProperties": False,
        },
        "reason": string,
    }
    return {
        "type": "json_schema",
        "name": FORMAT_NAME,
        "strict": True,
        "schema": {
            "type": "object",
            "properties": fields,
            "required": list(fields),
            "additionalProperties": False,
        },
    }


def _attr(obj: Any, name: str, default=None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def validate_response_envelope(response: Any) -> Any:
    """Fail closed before passing incomplete/refused outputs to the scorer.

    A normal completed response is returned unchanged. The inherited
    transport-retry/pause logic handles the raised errors, so no unstructured
    request is silently substituted.
    """
    status = _attr(response, "status")
    if status is not None and status != "completed":
        raise ValueError(f"Structured output status is {status!r}, not completed")
    for item in _attr(response, "output", []) or []:
        for part in _attr(item, "content", []) or []:
            if _attr(part, "type") == "refusal" or _attr(part, "refusal"):
                raise ValueError("Structured output was refused by the model")
    if _attr(response, "incomplete_details"):
        raise ValueError("Structured output contains incomplete_details")
    return response


class _ResponsesWithCardSchema:
    """One-call proxy: inject schema only into the matching reward API call."""

    def __init__(self, original: Any, format_spec: dict[str, Any]):
        self._original = original
        self._format_spec = format_spec

    def create(self, *args: Any, **kwargs: Any) -> Any:
        if "text" in kwargs:
            raise ValueError("Card reward request already has a text format")
        result = self._original.create(
            *args, text={"format": self._format_spec}, **kwargs
        )
        return validate_response_envelope(result)


class _ClientWithCardSchema:
    """Only the Responses API .create() surface is needed by inherited code."""

    def __init__(self, original: Any, format_spec: dict[str, Any]):
        self.responses = _ResponsesWithCardSchema(
            original.responses, format_spec
        )
