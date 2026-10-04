from __future__ import annotations

from dataclasses import dataclass

from .models import AgentName, RoutingPlan


@dataclass(frozen=True)
class CrewTaskSpec:
    name: AgentName
    depends_on: tuple[AgentName, ...]


def build_task_specs(plan: RoutingPlan) -> list[CrewTaskSpec]:
    """Convert Router output into a deterministic CrewAI task graph."""
    return [
        CrewTaskSpec(name=step.name, depends_on=tuple(step.depends_on))
        for step in plan.agents
    ]
