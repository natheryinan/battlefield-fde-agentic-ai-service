from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, Optional, List, Protocol
import math
import copy
from types import MappingProxyType

from fde.kernel.risk_budget import RiskBudget




class RiskMode(Enum):
    SURVIVOR = "SURVIVOR"
    STABILIZE = "STABILIZE"
    PROBE = "PROBE"
    STRIKE = "STRIKE"
    SILENT = "SILENT"
    INDUCED_EXTREME = "INDUCED_EXTREME"

@dataclass(frozen=True)
class Action:
    kind: str
    payload: Dict[str, Any]

class Persona(Protocol):
    name: str
    priority: int
    def is_applicable(self, state: Dict[str, Any]) -> bool: ...
    def propose(self, state: Dict[str, Any], risk_mode: RiskMode) -> Optional[Action]: ...




def parse_risk_mode(raw: Any, control_flag: str = "SAFE") -> RiskMode:
    """
    control_flag:
      - "SAFE": never raise, fallback SILENT
      - "STRICT": raise ValueError if invalid
    """
    if isinstance(raw, RiskMode):
        return raw
    if isinstance(raw, str):
        try:
            return RiskMode(raw)
        except ValueError:
            if control_flag == "STRICT":
                raise
            return RiskMode.SILENT
    if control_flag == "STRICT":
        raise ValueError(f"Invalid risk_mode type: {type(raw)}")
    return RiskMode.SILENT

def deep_freeze_state_view(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Returns a read-only view for top-level keys.
    NOTE: nested dicts are still mutable unless you deep-freeze them; we block mutation
    by routing all writes to copies and enforcing Overlord non-mutation.
    """
    return MappingProxyType(state)  

def total_cost(state: Dict[str, Any], kpsi: float = 6.0) -> float:
    τ = float(state["time_pressure"])
    ψ = float(state["psych_load"])
    r = float(state["runway"].survival_index())
    return (1.0 / max(τ, 1e-9)) + (1.0 / max(r, 1e-9)) + math.exp(kpsi * max(0.0, ψ))

def safe_call_overlord_induce(overlord, original_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    HARD RULE: original_state must not be mutated.
    - We pass a deep copy into overlord.
    - We verify original_state is unchanged after call.
    - We return the induced copy.
    """
    before = copy.deepcopy(original_state)
    working = copy.deepcopy(original_state)

    out = overlord.induce_max(working)

    
