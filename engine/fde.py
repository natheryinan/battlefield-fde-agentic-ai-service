# engine/fde.py
from typing import Dict, List
from personas.base import BasePersona, MarketState
from personas.alpha import AlphaPersona
from personas.convexity import ConvexityPersona
from personas.liquidity import LiquidityPersona
from personas.guardian import GuardianPersona
from personas.regime import RegimePersona
from personas.macro import MacroPersona
from personas.anomaly import AnomalyPersona
from personas.benchmark import BenchmarkPersona
from personas.compliance import CompliancePersona

class FDEEngine:
    def __init__(self, personas: List[BasePersona] | None = None):
        self.personas = personas or [
            AlphaPersona(),
            ConvexityPersona(),
            LiquidityPersona(),
            GuardianPersona(),
            RegimePersona(),
            MacroPersona(),
            AnomalyPersona(),
            # benchmark / compliance usually configured with params
        ]

    def step(self, state: MarketState) -> Dict[str, float]:
        proposals: Dict[str, Dict[str, float]] = {}
        for p in self.personas:
            proposals[p.name] = p.act(state)

        aggregated: Dict[str, float] = {}
        for action in proposals.values():
            for symbol, delta in action.items():
                aggregated[symbol] = aggregated.get(symbol, 0.0) + delta
        return aggregated
