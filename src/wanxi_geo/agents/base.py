from __future__ import annotations

from pathlib import Path

from crewai import Agent, LLM


PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"


class BaseAgent:
    """Factory for a CrewAI Agent with an externalized operating prompt."""

    name: str
    role: str
    goal: str
    backstory: str
    prompt_file: str

    def operating_prompt(self) -> str:
        return (PROMPT_DIR / self.prompt_file).read_text(encoding="utf-8")

    def build(self, llm: LLM, *, verbose: bool = False) -> Agent:
        return Agent(
            role=self.role,
            goal=self.goal,
            backstory=(
                f"{self.backstory}\n\n"
                "You must follow this operating policy and output contract:\n"
                f"{self.operating_prompt()}"
            ),
            llm=llm,
            verbose=verbose,
            allow_delegation=False,
        )
