from src.llm.inference_client import LLMClient
from src.agents.planner_agent import PlannerAgent
from src.agents.retrieval_agent import RetrievalAgent
from src.agents.execution_agent import ExecutionAgent

def test_agent_pipeline():
    llm = LLMClient()
    planner = PlannerAgent(llm)
    retrieval = RetrievalAgent()
    executor = ExecutionAgent(llm, retrieval)

    steps = planner.plan("Test battlefield mission.")
    assert steps, "Planner should return at least one step"

    outputs = executor.execute_steps(steps)
    assert len(outputs) == len(steps)
