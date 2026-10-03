from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from ..llm import OpenAICompatibleClient


PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"


class BaseAgent(ABC):
    name: str
    prompt_file: str

    def __init__(self, llm: OpenAICompatibleClient):
        self.llm = llm

    def system_prompt(self) -> str:
        return (PROMPT_DIR / self.prompt_file).read_text(encoding="utf-8")

    @abstractmethod
    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError
