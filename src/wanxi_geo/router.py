from __future__ import annotations

from collections import OrderedDict
from typing import Iterable

from .llm import OpenAICompatibleClient
from .models import AgentName, RoutingPlan, RoutingStep


class HybridRouter:
    """Rule-first router with LLM fallback for vague requests."""

    RULES: dict[AgentName, tuple[str, ...]] = {
        "website_analyst": (
            "官网表达", "官网内容", "品牌定位", "产品能力", "服务对象",
            "核心表达", "官网目前", "表达了什么", "公司介绍", "介绍一下", "是什么", "做什么",
        ),
        "geo_diagnostic": (
            "geo", "ai引用", "ai 引用", "ai理解", "ai 理解", "被ai引用",
            "被 ai 引用", "优化", "诊断", "缺少", "哪里需要", "哪些内容适合",
        ),
        "question_generator": (
            "用户会怎么问", "客户会怎么问", "目标客户问题", "用户问题",
            "会问ai", "会问 ai", "可能提问", "问题列表", "queries", "query",
        ),
        "content_strategy": (
            "应该写什么", "写什么内容", "内容策略", "内容优化", "优化建议",
            "faq", "blog", "博客", "案例页", "案例", "产品页", "优先级",
        ),
    }

    ORDER: tuple[AgentName, ...] = (
        "website_analyst",
        "geo_diagnostic",
        "question_generator",
        "content_strategy",
    )

    def __init__(self, llm: OpenAICompatibleClient | None = None):
        self.llm = llm

    def route(self, question: str) -> RoutingPlan:
        normalized = question.lower().replace("chatgpt", "ai")
        scores: OrderedDict[AgentName, int] = OrderedDict()
        matched: dict[AgentName, list[str]] = {}
        for agent, keywords in self.RULES.items():
            hits = [kw for kw in keywords if kw.lower() in normalized]
            if hits:
                scores[agent] = len(hits)
                matched[agent] = hits

        if scores:
            selected = list(scores.keys())
            selected = self._with_dependencies(selected)
            reason_bits = [f"{a}: {', '.join(matched.get(a, []))}" for a in scores]
            return self._build_plan(
                selected,
                intent=self._intent_name(selected),
                source="rules",
                reason="规则命中：" + "；".join(reason_bits),
            )

        if self.llm is not None:
            try:
                data = self.llm.chat_json(
                    self._router_prompt(),
                    f"USER_QUESTION:\n{question}",
                )
                raw_agents = data.get("agents", [])
                selected = [a for a in raw_agents if a in self.ORDER]
                if selected:
                    selected = self._with_dependencies(selected)
                    return self._build_plan(
                        selected,
                        intent=str(data.get("intent", "complex_request")),
                        source="llm",
                        reason=str(data.get("reason", "LLM Router selected agents.")),
                    )
            except Exception:
                pass

        return self._build_plan(
            ["website_analyst"],
            intent="website_understanding",
            source="fallback",
            reason="没有明确命中规则且 LLM Router 不可用，安全回退到官网信息分析。",
        )

    def _with_dependencies(self, agents: Iterable[AgentName]) -> list[AgentName]:
        selected = set(agents)
        if selected - {"website_analyst"}:
            selected.add("website_analyst")
        if "content_strategy" in selected:
            selected.add("geo_diagnostic")
        return [a for a in self.ORDER if a in selected]

    def _build_plan(
        self,
        selected: list[AgentName],
        *,
        intent: str,
        source: str,
        reason: str,
    ) -> RoutingPlan:
        steps: list[RoutingStep] = []
        for agent in selected:
            deps: list[AgentName] = []
            if agent in {"geo_diagnostic", "question_generator"}:
                deps = ["website_analyst"]
            elif agent == "content_strategy":
                deps = ["website_analyst"]
                if "geo_diagnostic" in selected:
                    deps.append("geo_diagnostic")
                if "question_generator" in selected:
                    deps.append("question_generator")
            steps.append(RoutingStep(name=agent, depends_on=deps))
        return RoutingPlan(intent=intent, source=source, reason=reason, agents=steps)

    @staticmethod
    def _intent_name(selected: list[AgentName]) -> str:
        if selected == ["website_analyst"]:
            return "website_understanding"
        if "content_strategy" in selected:
            return "content_strategy"
        if "question_generator" in selected and "geo_diagnostic" not in selected:
            return "customer_question_generation"
        if "geo_diagnostic" in selected:
            return "geo_audit"
        return "complex_request"

    @staticmethod
    def _router_prompt() -> str:
        return """You are a task router for a GEO website analysis system.
Available agents:
- website_analyst: summarize brand/product/technical/customer information from website evidence.
- geo_diagnostic: evaluate whether website content is easy for AI systems to understand, extract and cite.
- question_generator: generate realistic target-customer questions to AI assistants.
- content_strategy: recommend FAQ/Blog/case/product content based on previous analysis.

Choose only agents needed for the request. Dependencies are added later by the orchestrator.
Return JSON: {"intent":"...","agents":["..."],"reason":"..."}.
Do not invent website facts."""
