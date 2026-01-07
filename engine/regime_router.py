# engine/regime_router.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from engine.persona_roles import Persona


@dataclass
class AdvisorEvent:
    """
    单步结果（只属于此刻）：
    - advisor: 此刻顾问位（或主独行 = None）
    - event : 就位 / 持续压紧 / 位移·不中断 / 围猎
    """
    advisor: Optional[Persona]
    event: str

def step(self, band: str) -> AdvisorEvent:
    prev_advisor = self._last_advisor
    advisor = self._select_advisor(band)

    if prev_advisor is None and advisor is None:
        event = "围猎"
    elif prev_advisor is None and advisor is not None:
        event = "就位"
    elif prev_advisor == advisor and advisor is not None:
        event = "持续压紧"
    elif (
        prev_advisor is not None
        and advisor is not None
        and advisor != prev_advisor
    ):
        event = "位移·不中断"
    elif prev_advisor is not None and advisor is None:
        event = "围猎"
    else:
        event = "围猎"

    self._last_advisor = advisor
    return AdvisorEvent(advisor=advisor, event=event)




