from typing import List
from src.utils.logger import get_logger

logger = get_logger(__name__)

def simple_quality_score(outputs: List[str]) -> float:
    """
    Toy evaluation: score based on non-empty outputs.
    """
    if not outputs:
        return 0.0
    non_empty = [o for o in outputs if o.strip()]
    score = len(non_empty) / len(outputs)
    logger.info("Simple quality score: %s", score)
    return score
