
from dataclasses import dataclass
from typing import Optional
from fde.kernel.sovereign_router import Action, RiskMode

@dataclass
class AlphaProbePersona:
    name: str = "AlphaProbe"
    priority: int = 71

    def is_applicable(self, state) -> bool:
        return state.get("risk_mode") in (RiskMode.PROBE.value,)

    def propose(self, state, risk_mode: RiskMode) -> Optional[Action]:
        return Action(kind="ALPHA_PROBE_EXEC", payload={
            "risk_mode": risk_mode.value,
            "size": float(state.get("alpha_probe_size", 0.25)),
            "exploration": float(state.get("alpha_probe_exploration", 0.4)),
        })
