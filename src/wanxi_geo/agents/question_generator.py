from __future__ import annotations

import json
from typing import Any

from .base import BaseAgent


class QuestionGeneratorAgent(BaseAgent):
    name = "question_generator"
    prompt_file = "question_generator.md"

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        profile = state["results"].get("website_analyst", {})
        user = f"""USER_QUESTION:
{state['question']}

WEBSITE_PROFILE:
{json.dumps(profile, ensure_ascii=False, indent=2)}
"""
        data = self.llm.chat_json(self.system_prompt(), user)
        defaults = {"personas": [], "questions": [], "coverage_notes": []}
        return {**defaults, **data}
