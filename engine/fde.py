
from typing import Dict, Any
import random

def tiny_chance_gate(state: Dict[str, Any], p_min: float = 0.01) -> float:
    r = float(state["runway"].survival_index())
    ψ = float(state["psych_load"])
    τ = float(state["time_pressure"])

    extreme = (r < 0.5) or (ψ > 0.8) or (τ < 0.2)
    return p_min if extreme else 0.10

class FDE:
    def __init__(self, router):
        self._router = router

    def step(self, state: Dict[str, Any]) -> Dict[str, Any]:
        p = tiny_chance_gate(state, p_min=float(state.get("tiny_p_min", 0.01)))
        state["tiny_chance_p"] = p

        
        state["tiny_probe_ok"] = (random.random() < p)

        action = self._router.route(state)
        return {"action": action, "state": state}
