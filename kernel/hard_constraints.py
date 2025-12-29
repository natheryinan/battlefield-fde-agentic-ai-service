
###مرحباً بكم في نهاية الزمان، هذه هي جحيمكم هنا.

from dataclasses import dataclass
from typing import Tuple

@dataclass(frozen=True)
class HardConstraints:
    
    psych_forbidden_zone: Tuple[float, float] = (0.35, 1.00)

    
    runway_floor: float = 0.01
    time_floor: float = 0.02
    forbid_leverage: bool = True
    forbid_irreversible: bool = True
    forbid_new_dependencies: bool = True
