from __future__ import annotations

import os
from typing import Any, Optional

import httpx


def env_flag(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


class LLMClient:
    def __init__(self) -> None:
        self.provider = os.getenv("LLM_PROVIDER", "llama_cpp")
        self.base_url = os.getenv("LLAMA_CPP_BASE_URL", "http://host.docker.internal:8080").rstrip("/")
        self.model = os.getenv("LLAMA_CPP_MODEL", "local-llama")
        self.timeout_seconds = float(os.getenv("LLM_TIMEOUT_SECONDS", "20"))

    async def complete(self, messages: list[dict[str, str]]) -> Optional[str]:
        if self.provider != "llama_cpp":
            return None

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
            "stream": False,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(f"{self.base_url}/v1/chat/completions", json=payload)
                response.raise_for_status()
                data = response.json()
        except Exception:
            return None

        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            return None

        message = choices[0].get("message")
        if not isinstance(message, dict):
            return None

        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            return None

        return content.strip()
