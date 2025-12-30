
# personas/anomaly.py
from typing import Dict
from .base import BasePersona, MarketState

class AnomalyPersona(BasePersona):
    name = "anomaly"

    def act(self, state: MarketState) -> Dict[str, float]:
        # TODO: anomaly / outlier detection
        return {}
