
from dataclasses import dataclass
from typing import Optional
from fde.kernel.sovereign_router import Action, RiskMode

@dataclass
class AlphaStrikePersona:
    name: str = "AlphaStrike"
    priority: int = 72

    def is_applicable(self, state) -> bool:
        return state.get("risk_mode") in (RiskMode.STRIKE.value, RiskMode.INDUCED_EXTREME.value)

    def propose(self, state, risk_mode: RiskMode) -> Optional[Action]:
        return Action(kind="ALPHA_STRIKE_EXEC", payload={
            "risk_mode": risk_mode.value,
            "size": float(state.get("alpha_strike_size", 1.5)),
            "aggressiveness": float(state.get("alpha_strike_aggr", 0.9)),
        })
