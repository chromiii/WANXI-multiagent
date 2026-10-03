from __future__ import annotations

import json
import time
from typing import Any

from .agents import (
    ContentStrategyAgent,
    GeoDiagnosticAgent,
    QuestionGeneratorAgent,
    WebsiteAnalystAgent,
)
from .llm import OpenAICompatibleClient
from .models import AgentTrace, RunResult, SiteDocument
from .router import HybridRouter


class AgentOrchestrator:
    def __init__(self, llm: OpenAICompatibleClient):
        self.llm = llm
        self.router = HybridRouter(llm)
        self.agents = {
            "website_analyst": WebsiteAnalystAgent(llm),
            "geo_diagnostic": GeoDiagnosticAgent(llm),
            "question_generator": QuestionGeneratorAgent(llm),
            "content_strategy": ContentStrategyAgent(llm),
        }

    def run(self, question: str, documents: list[SiteDocument]) -> RunResult:
        plan = self.router.route(question)
        state: dict[str, Any] = {
            "question": question,
            "documents": documents,
            "results": {},
        }
        traces: list[AgentTrace] = []

        for step in plan.agents:
            missing = [dep for dep in step.depends_on if dep not in state["results"]]
            if missing:
                traces.append(
                    AgentTrace(
                        agent=step.name,
                        status="failed",
                        duration_ms=0,
                        error=f"Missing dependencies: {missing}",
                    )
                )
                continue

            started = time.perf_counter()
            try:
                result = self.agents[step.name].run(state)
                state["results"][step.name] = result
                traces.append(
                    AgentTrace(
                        agent=step.name,
                        status="completed",
                        duration_ms=int((time.perf_counter() - started) * 1000),
                        result=result,
                    )
                )
            except Exception as exc:
                traces.append(
                    AgentTrace(
                        agent=step.name,
                        status="failed",
                        duration_ms=int((time.perf_counter() - started) * 1000),
                        error=str(exc),
                    )
                )

        final_answer = self._synthesize(question, plan.model_dump(), state["results"])
        return RunResult(
            question=question,
            routing=plan,
            agent_traces=traces,
            agent_results=state["results"],
            final_answer=final_answer,
        )

    def _synthesize(
        self,
        question: str,
        routing: dict[str, Any],
        results: dict[str, Any],
    ) -> str:
        if not results:
            return (
                "没有 Agent 成功完成任务。请检查 Ollama / API 配置和网站抓取结果，"
                "再重试。"
            )

        prompt = (self._prompt_dir() / "synthesizer.md").read_text(encoding="utf-8")
        user = f"""USER_QUESTION:
{question}

ROUTING_PLAN:
{json.dumps(routing, ensure_ascii=False, indent=2)}

AGENT_RESULTS:
{json.dumps(results, ensure_ascii=False, indent=2)}
"""
        try:
            return self.llm.chat(prompt, user, temperature=0.1)
        except Exception:
            return self._fallback_markdown(results)

    @staticmethod
    def _prompt_dir():
        from pathlib import Path

        return Path(__file__).resolve().parent / "prompts"

    @staticmethod
    def _fallback_markdown(results: dict[str, Any]) -> str:
        parts = ["## Agent Results"]
        for name, result in results.items():
            parts.append(
                f"\n### {name}\n```json\n"
                f"{json.dumps(result, ensure_ascii=False, indent=2)}\n```"
            )
        return "\n".join(parts)
