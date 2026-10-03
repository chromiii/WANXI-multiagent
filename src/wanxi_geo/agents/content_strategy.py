from __future__ import annotations

import json
from typing import Any

from .base import BaseAgent


class ContentStrategyAgent(BaseAgent):
    name = "content_strategy"
    prompt_file = "content_strategy.md"

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "website_profile": state["results"].get("website_analyst", {}),
            "geo_diagnosis": state["results"].get("geo_diagnostic", {}),
            "customer_questions": state["results"].get("question_generator", {}),
        }
        user = f"""USER_QUESTION:
{state['question']}

UPSTREAM_RESULTS:
{json.dumps(payload, ensure_ascii=False, indent=2)}
"""
        data = self.llm.chat_json(self.system_prompt(), user)
        defaults = {
            "recommendations": [],
            "priority_plan": [],
            "measurement_ideas": [],
            "summary": "",
        }
        return {**defaults, **data}
