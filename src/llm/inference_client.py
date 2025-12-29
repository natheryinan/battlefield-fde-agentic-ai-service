from typing import List
from . import prompt_templates
from src.utils.logger import get_logger
from src.utils.config import settings

logger = get_logger(__name__)

class LLMClient:
    """
    Thin wrapper around an LLM provider.

    For this demo, we don't actually call a provider. We simulate responses so
    the project runs anywhere. To use a real model, replace these methods with
    real OpenAI / Anthropic / local-model calls.
    """

    def __init__(self) -> None:
        self.model_name = settings.model_name
        if not settings.openai_api_key:
            logger.info(
                "OPENAI_API_KEY not set – using fake responses. "
                "Wire in a provider in `generate_plan` / `generate_execution` "
                "if you want real LLM calls."
            )

    def generate_plan(self, task: str) -> List[str]:
        """
        Return a list of execution steps for the given mission.
        """
        logger.info("Generating plan for task: %s", task)
        # In a real system, you would call an LLM here using
        # prompt_templates.planning_prompt(task)
        fake = [
            "Clarify mission requirements and constraints.",
            "Identify data sources and retrieval tools.",
            "Design agent workflow (planner, retrieval, execution).",
            "Implement and test the pipeline end-to-end.",
            "Deploy API and monitor live signals.",
        ]
        return fake

    def generate_execution(self, step: str, context: str | None = None) -> str:
        """
        Return an execution summary for a single step.
        """
        logger.info("Generating execution output for step: %s", step)
        # In a real system, call an LLM using prompt_templates.execution_prompt(...)
        return f"[SIMULATED EXECUTION OF STEP] {step}"
