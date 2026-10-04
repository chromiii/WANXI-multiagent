from .base import BaseAgent


class FinalSynthesizerAgent(BaseAgent):
    name = "final_synthesizer"
    role = "GEO Analysis Lead"
    goal = (
        "Integrate the selected agents' outputs into one clear answer that directly addresses "
        "the user while preserving evidence, recommendations and uncertainty boundaries."
    )
    backstory = (
        "You are the lead analyst responsible for turning specialist outputs into a concise "
        "business-ready report without introducing any new company facts."
    )
    prompt_file = "synthesizer.md"
