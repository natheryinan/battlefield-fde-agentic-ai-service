
from dataclasses import dataclass
from typing import Optional
from fde.kernel.sovereign_router import Action, RiskMode

@dataclass
class KidPersona:
    name: str = "KID"
    priority: int = 50

    def is_applicable(self, state) -> bool:
        return bool(state.get("lord_debug_kid", False))

    def propose(self, state, risk_mode: RiskMode) -> Optional[Action]:
        return Action(kind="KID_VETO", payload={"scope": "guardian_only"})
