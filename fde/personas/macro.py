

# personas/macro.py
from typing import Dict
from .base import BasePersona, MarketState

class MacroPersona(BasePersona):
    name = "macro"

    def act(self, state: MarketState) -> Dict[str, float]:
        # TODO: macro signal based tilts
        return {}
