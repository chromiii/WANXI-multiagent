from __future__ import annotations

import json
from typing import Any

from .base import BaseAgent
from ..context import build_site_context


class GeoDiagnosticAgent(BaseAgent):
    name = "geo_diagnostic"
    prompt_file = "geo_diagnostic.md"

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        profile = state["results"].get("website_analyst", {})
        context = build_site_context(
            state["question"] + " GEO AI 引用 FAQ 产品 证据 定义",
            state["documents"],
            top_k=8,
        )
        user = f"""USER_QUESTION:
{state['question']}

WEBSITE_PROFILE_FROM_UPSTREAM_AGENT:
{json.dumps(profile, ensure_ascii=False, indent=2)}

SITE_CONTEXT:
{context}
"""
        data = self.llm.chat_json(self.system_prompt(), user)
        defaults = {
            "strengths": [],
            "gaps": [],
            "rubric": {},
            "missing_content": [],
            "summary": "",
        }
        return {**defaults, **data}
