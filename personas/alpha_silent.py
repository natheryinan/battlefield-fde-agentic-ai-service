
from dataclasses import dataclass
from typing import Optional
from fde.kernel.sovereign_router import Action, RiskMode

@dataclass
class AlphaSilentPersona:
    name: str = "AlphaSilent"
    priority: int = 69

    def is_applicable(self, state) -> bool:
        return state.get("risk_mode") in (RiskMode.SILENT.value,)

    def propose(self, state, risk_mode: RiskMode) -> Optional[Action]:
        return Action(kind="HOLD", payload={"risk_mode": risk_mode.value})
