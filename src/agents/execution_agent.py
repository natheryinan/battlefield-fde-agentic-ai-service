from typing import List
from src.llm.inference_client import LLMClient
from src.utils.logger import get_logger
from .retrieval_agent import RetrievalAgent

logger = get_logger(__name__)

class ExecutionAgent:
    """
    Executes each planned step using tools, retrieval, and the LLM.
    """

    def __init__(self, llm: LLMClient, retrieval_agent: RetrievalAgent) -> None:
        self.llm = llm
        self.retrieval_agent = retrieval_agent

    def execute_steps(self, steps: List[str]) -> List[str]:
        results: List[str] = []
        for step in steps:
            context_list = self.retrieval_agent.retrieve(step)
            context = "\n".join(context_list)
            output = self.llm.generate_execution(step, context=context)
            logger.info("Executed step: %s", step)
            results.append(output)
        return results
