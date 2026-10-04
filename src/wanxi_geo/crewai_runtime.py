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

    SYNTH_SECTION_BY_AGENT: dict[str, str] = {
        "website_analyst": "官网现状 / 关键发现",
        "geo_diagnostic": "GEO 诊断",
        "question_generator": "目标客户问题",
        "content_strategy": "内容优化建议与优先级",
    }

    SYNTH_FORBIDDEN_BY_AGENT: dict[str, str] = {
        "geo_diagnostic": (
            "Do not perform GEO diagnosis, create GEO strengths/gaps, or assign GEO rubric scores."
        ),
        "question_generator": (
            "Do not generate customer questions, personas, customer stages, or inferred query lists."
        ),
        "content_strategy": (
            "Do not create content recommendations, P0/P1/P2 priorities, roadmaps, or future strategy."
        ),
    }

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
            expected_output=self._synth_expected_output(ordered_names),
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

    @classmethod
    def _synth_task_description(cls, question: str, ordered_names: list[str]) -> str:
        roster = ", ".join(ordered_names)
        required_sections = [
            "本次调用的 Agent 与原因",
            *[
                cls.SYNTH_SECTION_BY_AGENT[name]
                for name in ordered_names
                if name in cls.SYNTH_SECTION_BY_AGENT
            ],
            "引用依据 / source URLs",
            "边界与不确定性",
        ]

        forbidden_work = [
            instruction
            for agent, instruction in cls.SYNTH_FORBIDDEN_BY_AGENT.items()
            if agent not in ordered_names
        ]

        output_limits: list[str] = [
            "Use only the supplied specialist task outputs.",
            "Do not add new company facts.",
            "Do not create a report section that is not listed in REQUIRED_SECTION_ORDER.",
            "Omit absent specialist work entirely instead of filling it in yourself.",
            "Preserve material source URLs and clearly state evidence limitations.",
        ]
        if "geo_diagnostic" in ordered_names:
            output_limits.append("Summarize at most 4 GEO strengths and 5 GEO gaps.")
        if "question_generator" in ordered_names:
            output_limits.append("Show at most 8 representative customer questions.")
        if "content_strategy" in ordered_names:
            output_limits.append(
                "Show at most 8 content recommendations while preserving P0/P1/P2 priority."
            )

        sections_text = "\n".join(
            f"{index}. {section}" for index, section in enumerate(required_sections, start=1)
        )
        forbidden_text = (
            "\n".join(f"- {item}" for item in forbidden_work)
            if forbidden_work
            else "- None. All specialist capabilities in this workflow were selected."
        )
        limits_text = "\n".join(f"- {item}" for item in output_limits)

        return (
            "Answer the original user question by integrating only the selected specialist task "
            "outputs. The following final-report contract is authoritative.\n\n"
            f"ORIGINAL_USER_QUESTION:\n{question}\n\n"
            f"SELECTED_SPECIALIST_COUNT: {len(ordered_names)}\n"
            f"SELECTED_SPECIALIST_AGENTS: {roster}\n"
            "INTEGRATION_AGENT: final_synthesizer\n\n"
            "REQUIRED_SECTION_ORDER:\n"
            f"{sections_text}\n\n"
            "FORBIDDEN_WORK:\n"
            f"{forbidden_text}\n\n"
            "OUTPUT_RULES:\n"
            f"{limits_text}\n\n"
            "The selected-agent roster, section order, forbidden work, and output rules above "
            "must be followed exactly. final_synthesizer is an integration/presentation layer, "
            "not a substitute specialist."
        )

    @classmethod
    def _synth_expected_output(cls, ordered_names: list[str]) -> str:
        sections = [
            "本次调用的 Agent 与原因",
            *[
                cls.SYNTH_SECTION_BY_AGENT[name]
                for name in ordered_names
                if name in cls.SYNTH_SECTION_BY_AGENT
            ],
            "引用依据 / source URLs",
            "边界与不确定性",
        ]
        return (
            "A concise Chinese Markdown report containing exactly these report sections in order: "
            + " | ".join(sections)
            + ". Do not add sections for unselected specialist capabilities."
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
