from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


AgentName = Literal[
    "website_analyst",
    "geo_diagnostic",
    "question_generator",
    "content_strategy",
]


class SiteDocument(BaseModel):
    url: str
    title: str = ""
    headings: list[str] = Field(default_factory=list)
    text: str
    links: list[str] = Field(default_factory=list)


class RoutingStep(BaseModel):
    name: AgentName
    depends_on: list[AgentName] = Field(default_factory=list)


class RoutingPlan(BaseModel):
    intent: str
    source: Literal["rules", "llm", "fallback"] = "rules"
    reason: str
    agents: list[RoutingStep]


class AgentTrace(BaseModel):
    agent: AgentName
    status: Literal["completed", "failed"]
    duration_ms: int
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class RunResult(BaseModel):
    question: str
    routing: RoutingPlan
    agent_traces: list[AgentTrace]
    agent_results: dict[str, Any]
    final_answer: str
