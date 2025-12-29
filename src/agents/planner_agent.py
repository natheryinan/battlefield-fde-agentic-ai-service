from typing import List
from src.llm.inference_client import LLMClient

class PlannerAgent:
    """
    Decomposes a high-level mission into smaller execution steps.
    """

    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def plan(self, mission: str) -> List[str]:
        return self.llm.generate_plan(mission)
