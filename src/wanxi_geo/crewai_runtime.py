from __future__ import annotations

from typing import Any

from crewai import Crew, LLM, Process, Task

from .agents import (
    ContentStrategyAgent,
    FinalSynthesizerAgent,
    GeoDiagnosticAgent,
    QuestionGeneratorAgent,
    WebsiteAnalystAgent,
)
from .config import Settings
from .context import build_site_context
from .crew_plan import build_task_specs
from .llm import LLMError, extract_json_object
from .models import AgentTrace, RoutingPlan, RunResult, SiteDocument


def build_crewai_llm(settings: Settings) -> LLM:
    """Build one CrewAI LLM for Ollama, DeepSeek or another OpenAI-compatible endpoint."""
    return LLM(
        model=settings.llm_model,
        custom_openai=True,
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        temperature=settings.llm_temperature,
    )


class CrewAIRuntime:
    """Translate Router plans into CrewAI Agents, Tasks and a sequential Crew."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.llm = build_crewai_llm(settings)
        self.agent_factories = {
            "website_analyst": WebsiteAnalystAgent(),
            "geo_diagnostic": GeoDiagnosticAgent(),
            "question_generator": QuestionGeneratorAgent(),
            "content_strategy": ContentStrategyAgent(),
        }
        self.synthesizer_factory = FinalSynthesizerAgent()

    def run(
        self,
        question: str,
        documents: list[SiteDocument],
        plan: RoutingPlan,
    ) -> RunResult:
        specs = build_task_specs(plan)
        agents: dict[str, Any] = {
            spec.name: self.agent_factories[spec.name].build(
                self.llm, verbose=self.settings.crewai_verbose
            )
            for spec in specs
        }
        synthesizer = self.synthesizer_factory.build(
            self.llm, verbose=self.settings.crewai_verbose
        )

        tasks: dict[str, Task] = {}
        ordered_tasks: list[Task] = []
        ordered_names: list[str] = []

        for spec in specs:
            context_tasks = [tasks[name] for name in spec.depends_on if name in tasks]
            task = Task(
                description=self._task_description(spec.name, question, documents),
                expected_output=self._expected_output(spec.name),
                agent=agents[spec.name],
                context=context_tasks or None,
            )
            tasks[spec.name] = task
            ordered_tasks.append(task)
            ordered_names.append(spec.name)

        synth_task = Task(
            description=self._synth_task_description(question, ordered_names),
            expected_output=(
                "A concise Chinese Markdown report that directly answers the user, uses the "
                "authoritative specialist-agent roster/count, preserves material source URLs, "
                "separates facts from diagnosis/recommendations, and states uncertainty."
            ),
            agent=synthesizer,
            context=ordered_tasks,
            markdown=True,
        )

        crew = Crew(
            agents=[*agents.values(), synthesizer],
            tasks=[*ordered_tasks, synth_task],
            process=Process.sequential,
            verbose=self.settings.crewai_verbose,
        )
        output = crew.kickoff()

        task_outputs = list(getattr(output, "tasks_output", []) or [])
        results: dict[str, Any] = {}
        traces: list[AgentTrace] = []

        for index, name in enumerate(ordered_names):
            raw = self._raw_output(task_outputs, index)
            try:
                parsed = extract_json_object(raw)
                results[name] = parsed
                traces.append(
                    AgentTrace(agent=name, status="completed", result=parsed)
                )
            except LLMError as exc:
                fallback = {"raw": raw, "_warning": str(exc)}
                results[name] = fallback
                traces.append(
                    AgentTrace(agent=name, status="completed", result=fallback)
                )

        final_raw = self._raw_output(task_outputs, len(ordered_names))
        if not final_raw:
            final_raw = str(getattr(output, "raw", output))
        traces.append(
            AgentTrace(
                agent="final_synthesizer",
                status="completed",
                result={"markdown": final_raw},
            )
        )

        return RunResult(
            question=question,
            routing=plan,
            agent_traces=traces,
            agent_results=results,
            final_answer=final_raw,
            framework="CrewAI",
            crew_process="sequential",
        )

    @staticmethod
    def _raw_output(outputs: list[Any], index: int) -> str:
        if index >= len(outputs):
            return ""
        item = outputs[index]
        raw = getattr(item, "raw", item)
        return str(raw or "").strip()

    @staticmethod
    def _expected_output(name: str) -> str:
        if name == "website_analyst":
            return "One concise valid JSON object matching the Website Analyst operating prompt."
        if name == "geo_diagnostic":
            return "One concise valid JSON object matching the GEO Diagnostic operating prompt."
        if name == "question_generator":
            return "One concise valid JSON object matching the Question Generator operating prompt."
        if name == "content_strategy":
            return "One concise valid JSON object matching the Content Strategy operating prompt."
        raise ValueError(f"Unknown task name: {name}")

    @staticmethod
    def _synth_task_description(question: str, ordered_names: list[str]) -> str:
        roster = ", ".join(ordered_names)
        return (
            "Answer the original user question by integrating the specialist task outputs.\n\n"
            f"ORIGINAL_USER_QUESTION:\n{question}\n\n"
            f"SELECTED_SPECIALIST_COUNT: {len(ordered_names)}\n"
            f"SELECTED_SPECIALIST_AGENTS: {roster}\n"
            "INTEGRATION_AGENT: final_synthesizer\n\n"
            "The roster/count above are authoritative. Do not rename, recount or change them. "
            "Do not count final_synthesizer as a selected specialist. "
            "Do not introduce new company facts. Clearly separate observed website facts, "
            "GEO interpretations, and future recommendations. Prefer high-value findings over "
            "repeating every upstream item."
        )

    @staticmethod
    def _task_description(
        name: str,
        question: str,
        documents: list[SiteDocument],
    ) -> str:
        if name == "website_analyst":
            site_context = build_site_context(
                question + " 品牌定位 产品能力 技术关键词 服务对象 核心表达 公司介绍",
                documents,
                top_k=8,
            )
            return (
                "Build the evidence-grounded website profile needed for the user request.\n\n"
                f"USER_QUESTION:\n{question}\n\nSITE_CONTEXT:\n{site_context}"
            )

        if name == "geo_diagnostic":
            site_context = build_site_context(
                question + " GEO AI 引用 FAQ 产品 证据 定义",
                documents,
                top_k=8,
            )
            return (
                "Perform a GEO citation-readiness audit. The Website Analyst output is supplied "
                "through CrewAI task context; use it together with the raw site evidence below.\n\n"
                f"USER_QUESTION:\n{question}\n\nSITE_CONTEXT:\n{site_context}"
            )

        if name == "question_generator":
            return (
                "Generate realistic target-customer questions for AI assistants. The Website "
                "Analyst output is supplied through CrewAI task context.\n\n"
                f"USER_QUESTION:\n{question}"
            )

        if name == "content_strategy":
            return (
                "Produce a prioritized GEO content roadmap. Relevant upstream Agent outputs are "
                "supplied through CrewAI task context; explicitly tie recommendations to those "
                "findings/questions. Make deliberate trade-offs instead of an exhaustive list.\n\n"
                f"USER_QUESTION:\n{question}"
            )

        raise ValueError(f"Unknown task name: {name}")
