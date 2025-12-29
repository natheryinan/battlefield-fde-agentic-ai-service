
from dataclasses import dataclass
from typing import Optional
from fde.kernel.sovereign_router import Action, RiskMode

@dataclass
class FireLayerPersona:
    name: str = "FireLayer"
    priority: int = 60

    def is_applicable(self, state) -> bool:
        r = state["runway"].survival_index()
        return r <= state.get("firelayer_on_r", 1.0)   

    def propose(self, state, risk_mode: RiskMode) -> Optional[Action]:
        return Action(
            kind="INDUCE_MAX",
            payload={"risk_mode": risk_mode.value, "attach_to_engine": True}
        )

