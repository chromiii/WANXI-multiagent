from __future__ import annotations

import json
import re
from typing import Any

import httpx

from .config import Settings


class LLMError(RuntimeError):
    pass


def extract_json_object(raw: str) -> dict[str, Any]:
    """Best-effort JSON extraction for local models that may add code fences."""
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise LLMError(f"Model did not return JSON: {raw[:500]}")
        try:
            value = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError as exc:
            raise LLMError(f"Invalid JSON from model: {raw[:800]}") from exc

    if not isinstance(value, dict):
        raise LLMError("Expected a JSON object from model.")
    return value


class OpenAICompatibleClient:
    """Small OpenAI-compatible client used by the explicit semantic Router.

    Agent execution itself is handled by CrewAI.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.endpoint = settings.llm_base_url.rstrip("/") + "/chat/completions"

    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float | None = None,
    ) -> str:
        payload = {
            "model": self.settings.llm_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": (
                self.settings.llm_temperature if temperature is None else temperature
            ),
        }
        headers = {"Content-Type": "application/json"}
        if self.settings.llm_api_key:
            headers["Authorization"] = f"Bearer {self.settings.llm_api_key}"

        try:
            with httpx.Client(timeout=self.settings.llm_timeout) as client:
                response = client.post(self.endpoint, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            raise LLMError(
                f"LLM request failed ({self.settings.llm_provider} @ {self.endpoint}): {exc}"
            ) from exc

        try:
            return data["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            raise LLMError(f"Unexpected LLM response: {data}") from exc

    def chat_json(\n        self,\n        system_prompt: str,\n        user_prompt: str,\n        *,\n        temperature: float | None = None,\n    ) -> dict[str, Any]:
        strict_system = (
            system_prompt.rstrip()
            + "\n\nIMPORTANT: Return exactly one valid JSON object. "
            "Do not wrap it in Markdown and do not add commentary outside JSON."
        )
        raw = self.chat(strict_system, user_prompt, temperature=temperature)
        return extract_json_object(raw)

    @staticmethod
    def _extract_json(raw: str) -> dict[str, Any]:
        return extract_json_object(raw)
