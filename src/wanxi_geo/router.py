from __future__ import annotations

from collections import OrderedDict
from typing import Any, Iterable

from .llm import OpenAICompatibleClient
from .models import AgentName, RoutingPlan, RoutingStep


class HybridRouter:
    """LLM-first semantic router with deterministic dependency resolution and rule fallback."""

    FALLBACK_RULES: dict[AgentName, tuple[str, ...]] = {
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
        if self.llm is not None:
            try:
                return self._route_with_llm(question)
            except Exception:
                pass

        rule_plan = self._route_with_rules(question)
        if rule_plan is not None:
            return rule_plan

        return self._build_plan(
            ["website_analyst"],
            intent="website_understanding",
            source="safe_fallback",
            reason=(
                "LLM Router 不可用或输出无效，且降级规则无法可靠判断；"
                "安全回退到官网信息分析。"
            ),
        )

    def _route_with_llm(self, question: str) -> RoutingPlan:
        if self.llm is None:
            raise RuntimeError("LLM Router is not configured.")

        data = self.llm.chat_json(
            self._router_prompt(),
            f"USER_QUESTION:\n{question}",
            temperature=0.0,
        )
        selected, intent, reason = self._validate_llm_decision(data)
        selected = self._with_dependencies(selected)

        return self._build_plan(
            selected,
            intent=intent,
            source="llm",
            reason=reason,
        )

    def _route_with_rules(self, question: str) -> RoutingPlan | None:
        normalized = question.lower().replace("chatgpt", "ai")
        scores: OrderedDict[AgentName, int] = OrderedDict()
        matched: dict[AgentName, list[str]] = {}

        for agent, keywords in self.FALLBACK_RULES.items():
            hits = [kw for kw in keywords if kw.lower() in normalized]
            if hits:
                scores[agent] = len(hits)
                matched[agent] = hits

        if not scores:
            return None

        selected = self._with_dependencies(list(scores.keys()))
        reason_bits = [f"{agent}: {', '.join(matched[agent])}" for agent in scores]
        return self._build_plan(
            selected,
            intent=self._intent_name(selected),
            source="rules_fallback",
            reason=(
                "LLM Router 不可用或输出无效；使用确定性降级规则："
                + "；".join(reason_bits)
            ),
        )

    def _validate_llm_decision(
        self,
        data: dict[str, Any],
    ) -> tuple[list[AgentName], str, str]:
        raw_agents = data.get("agents")
        if not isinstance(raw_agents, list) or not raw_agents:
            raise ValueError("Router must return a non-empty agents list.")

        unknown = [
            value
            for value in raw_agents
            if not isinstance(value, str) or value not in self.ORDER
        ]
        if unknown:
            raise ValueError(f"Router returned unsupported agents: {unknown}")

        selected: list[AgentName] = []
        for value in raw_agents:
            if value not in selected:
                selected.append(value)

        intent = data.get("intent")
        reason = data.get("reason")
        if not isinstance(intent, str) or not intent.strip():
            raise ValueError("Router must return a non-empty intent.")
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("Router must return a non-empty reason.")

        return selected, intent.strip(), reason.strip()

    def _with_dependencies(self, agents: Iterable[AgentName]) -> list[AgentName]:
        selected = set(agents)

        if selected - {"website_analyst"}:
            selected.add("website_analyst")

        if "content_strategy" in selected:
            selected.add("geo_diagnostic")

        return [agent for agent in self.ORDER if agent in selected]

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

        return RoutingPlan(
            intent=intent,
            source=source,
            reason=reason,
            agents=steps,
        )

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
        return """You are the semantic intent router for a GEO website analysis system.

Your only responsibility is to infer the user's requested work and select the minimum set of specialist agents needed to satisfy it.

Available specialist agents:
- website_analyst: extracts and summarizes factual brand, product, technical, audience and company information from website evidence.
- geo_diagnostic: evaluates website content for clarity, answerability, evidence quality, semantic consistency and citation readiness.
- question_generator: derives realistic target-customer questions and information needs from the website profile.
- content_strategy: converts diagnosed gaps and user needs into prioritized future content recommendations.

Routing principles:
- Select agents from the allowed specialist-agent list only.
- Select an agent only when its specialist work is explicitly required by the user's request.
- Prefer the smallest sufficient set of specialists.
- Do not infer extra deliverables merely because they could be useful.
- Do not add prerequisite agents for dependency reasons; dependency resolution is handled deterministically after routing.
- Base the decision on semantic intent, not keyword matching.
- Do not answer the user's business question and do not invent website facts.

Return exactly one JSON object with these required fields:
- intent: a concise snake_case label describing the requested task.
- agents: a non-empty array containing only allowed specialist-agent names.
- reason: a concise explanation of why those specialists are necessary for the user's request.

Do not include any other fields."""
