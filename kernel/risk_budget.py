
from dataclasses import dataclass

CRASH_BASELINE = 1.0
MELTDOWN_MULTIPLIER = 2.00

@dataclass(frozen=True)
class RiskBudget:
    legal: float
    cash: float
    time: float

    def total(self) -> float:
        return float(self.legal) + float(self.cash) + float(self.time)

def meltdown_index() -> float:
    return CRASH_BASELINE * MELTDOWN_MULTIPLIER
