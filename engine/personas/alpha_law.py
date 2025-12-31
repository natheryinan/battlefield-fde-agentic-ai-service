
# engine/personas/alpha_law.py
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class AlphaLawWindow:
    """
    A single 'law window' or 'blade slot' defined by Alpha.

    All violations & constraints are evaluated INSIDE this window.
    Nothing resets just because time passes; only when the law window changes.
    """
    covenant_id: str            # e.g. 
    slot_index: int        # 0, 1, 2, ...
    window_start: datetime
    window_end: datetime
    blade_triggered: bool = False   # once True, this slot is sealed


@dataclass
class BladeEvent:
    """
    Records a single blade action from Alpha within a window.
    """
    covenant_id: str
    slot_index: int
    at: datetime
    reason: str


class AlphaLawClock:
    """
    Outer bootstrap layer: the 'clock' of Alpha's law.

    - Holds current AlphaLawWindow.
    - Controls when a new slot opens.
    - Registers when Alpha uses the blade in a slot.
    """

    def __init__(self, initial_window: AlphaLawWindow):
        self._current_window = initial_window
        self._latest_blade_event: Optional[BladeEvent] = None

    @property
    def current_window(self) -> AlphaLawWindow:
        return self._current_window

    @property
    def latest_blade_event(self) -> Optional[BladeEvent]:
        return self._latest_blade_event

    def advance_window(self, new_window: AlphaLawWindow) -> None:
        """
        Move to the next Alpha law window.
        This is the ONLY natural reset for violation counts.
        """
        self._current_window = new_window
        self._latest_blade_event = None

    def register_blade(self, reason: str, when: Optional[datetime] = None) -> BladeEvent:
        """
        Alpha calls this once per slot when it uses the blade.

        After this:
        - current_window.blade_triggered == True
        - All non-Alpha personas are locked down for this slot.
        """
        when = when or datetime.utcnow()
        self._current_window = replace(self._current_window, blade_triggered=True)

        event = BladeEvent(
            covenant_id=self._current_window.law_id,
            slot_index=self._current_window.slot_index,
            at=when,
            reason=reason,
        )
        self._latest_blade_event = event
        return event
