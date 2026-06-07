from __future__ import annotations

from functools import lru_cache
from typing import Any

from .actions import evaluate_input_text, evaluate_output_text


class GuardrailsRunner:
    def __init__(self) -> None:
        self.framework = "local-rule-checks"

    async def check_input(self, text: str) -> dict[str, Any]:
        decision = evaluate_input_text(text)
        return self._response(decision)

    async def check_output(self, text: str) -> dict[str, Any]:
        decision = evaluate_output_text(text)
        return self._response(decision)

    def _response(self, decision: dict[str, Any]) -> dict[str, Any]:
        return {
            "pass": decision["pass_"],
            "reason": decision["reason"],
            "safe_text": decision["safe_text"],
        }


@lru_cache
def get_guardrails_runner() -> GuardrailsRunner:
    return GuardrailsRunner()
