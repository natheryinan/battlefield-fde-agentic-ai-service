
from dataclasses import dataclass
from typing import Dict, Any

@dataclass(frozen=True)
class Runway:
    horizon_days: float
    burn_per_day: float
    access_score: float     
    reliability: float      
    slack: float           

    def survival_index(self) -> float:
     
        return (self.horizon_days * self.access_score * self.reliability) * (1.0 + self.slack)

def make_state(
    time_pressure: float,
    runway: Runway,
    psych_load: float,
    market: Dict[str, Any],
    threat: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "time_pressure": float(time_pressure),
        "runway": runway,                 
        "psych_load": float(psych_load),
        "market": market,
        "threat": threat,
        "cashflow": 0.0,                
    }
