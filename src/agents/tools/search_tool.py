from typing import List

def simple_search(query: str, corpus: List[str]) -> List[str]:
    """
    Extremely small placeholder search function.
    """
    query_lower = query.lower()
    return [doc for doc in corpus if query_lower in doc.lower()]
