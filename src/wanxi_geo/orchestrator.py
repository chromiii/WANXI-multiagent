from __future__ import annotations

from .config import Settings
from .crewai_runtime import CrewAIRuntime
from .llm import OpenAICompatibleClient
from .models import RunResult, SiteDocument
from .router import HybridRouter


class AgentOrchestrator:
    """Explicit Router + CrewAI execution.

    The Router stays outside the Crew so the assessment can inspect exactly why
    agents were selected. CrewAI then owns Agent/Task/Crew execution and task context.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.router = HybridRouter(OpenAICompatibleClient(settings))
        self.runtime = CrewAIRuntime(settings)

    def run(self, question: str, documents: list[SiteDocument]) -> RunResult:
        plan = self.router.route(question)
        return self.runtime.run(question, documents, plan)
