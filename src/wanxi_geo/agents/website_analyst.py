from __future__ import annotations

from typing import Any

from .base import BaseAgent
from ..context import build_site_context


class WebsiteAnalystAgent(BaseAgent):
    name = "website_analyst"
    prompt_file = "website_analyst.md"

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        query = (
            state["question"]
            + " 品牌定位 产品能力 技术关键词 服务对象 核心表达 公司介绍"
        )
        context = build_site_context(query, state["documents"], top_k=8)
        user = f"""USER_QUESTION:
{state['question']}

SITE_CONTEXT:
{context}
"""
        data = self.llm.chat_json(self.system_prompt(), user)
        return self._normalize(data)

    @staticmethod
    def _normalize(data: dict[str, Any]) -> dict[str, Any]:
        defaults = {
            "brand_positioning": [],
            "products_and_capabilities": [],
            "technical_keywords": [],
            "target_customers": [],
            "core_messages": [],
            "missing_information": [],
            "summary": "",
        }
        return {**defaults, **data}
