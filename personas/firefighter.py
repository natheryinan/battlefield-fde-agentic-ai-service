
from dataclasses import dataclass
from typing import Optional
from fde.kernel.sovereign_router import Action, RiskMode

@dataclass
class FirefighterPersona:
    name: str = "Firefighter"
    priority: int = 0

    def is_applicable(self, state) -> bool:
        return False  

    def propose(self, state, risk_mode: RiskMode) -> Optional[Action]:
        return None
