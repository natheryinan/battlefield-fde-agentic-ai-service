
# personas/regime.py
from typing import Dict
from .base import BasePersona, MarketState

class RegimePersona(BasePersona):
    name = "regime"

    def act(self, state: MarketState) -> Dict[str, float]:
        # TODO: regime detection logic
        return {}
