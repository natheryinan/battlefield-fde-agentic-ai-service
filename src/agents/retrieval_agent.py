from typing import List
from src.utils.logger import get_logger

logger = get_logger(__name__)

class RetrievalAgent:
    """
    Placeholder retrieval agent.

    In a real deployment this would talk to a search index, vector database,
    or other knowledge source.
    """

    def retrieve(self, query: str) -> List[str]:
        logger.info("Stub retrieval for query: %s", query)
        # Replace with real retrieval logic (BM25, vector search, etc.)
        return [f"[STUB CONTEXT FOR QUERY] {query}"]
