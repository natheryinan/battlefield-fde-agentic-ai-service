
# personas/compliance.py
from typing import Dict, Set
from .base import BasePersona, MarketState

class CompliancePersona(BasePersona):
    name = "compliance"

    def __init__(self, blacklist: Set[str] | None = None):
        self.blacklist = blacklist or set()

    def act(self, state: MarketState) -> Dict[str, float]:
        # Usually acts through router veto; by itself it can be neutral.
        return {}
