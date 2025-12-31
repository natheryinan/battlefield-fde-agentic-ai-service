
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional, Tuple

from .alpha_law import AlphaLawWindow


WindowKey = Tuple[str, str, int]  # (persona_name, covenant_id, slot_index)


@dataclass
class WindowViolationRecord:
    """
    Violations for a persona *inside a specific Alpha covenant window*.

    Nothing here spans across windows — a new window means a new covenant scope.
    """
    persona_name: str
    covenant_id: str
    slot_index: int
    count: int = 0
    first_violation_at: Optional[datetime] = None
    last_violation_at: Optional[datetime] = None
    last_reason: Optional[str] = None


@dataclass
class ViolationCounterConfig:
    """
    Thresholds for constraint behavior inside a covenant window.
    """
    # Violations tolerated before squeeze begins
    soft_limit_per_window: int = 1

    # Beyond this, persona is muted for the rest of the window
    hard_limit_per_window: int = 1

    # Minimum surviving capacity during squeeze (0 < m ≤ 1)
    min_multiplier: float = 0.2


class ViolationCounter:
    """
    Alpha-covenant–aware violation counter.

    Core rules:

    • Violations are keyed by (persona, covenant_id, slot_index)
    • Nothing "decays with time" — only a new covenant window resets state
    • If window.blade_triggered:
         — Alpha remains allowed
         — all non-Alpha personas are sealed to 0 for that window
    """

    def __init__(self, config: Optional[ViolationCounterConfig] = None):
        self.config = config or ViolationCounterConfig()
        self._records: Dict[WindowKey, WindowViolationRecord] = {}

    # ---------- helpers ----------

    def _key(self, persona_name: str, window: AlphaLawWindow) -> WindowKey:
        return (persona_name, window.covenant_id, window.slot_index)

    def _get_record(self, persona_name: str, window: AlphaLawWindow) -> WindowViolationRecord:
        k = self._key(persona_name, window)
        if k not in self._records:
            self._records[k] = WindowViolationRecord(
                persona_name=persona_name,
                covenant_id=window.covenant_id,
                slot_index=window.slot_index,
            )
        return self._records[k]

    # ---------- public API ----------

    def register_violation(
        self,
        persona_name: str,
        reason: str,
        window: AlphaLawWindow,
        when: Optional[datetime] = None,
    ) -> WindowViolationRecord:
        """
        Register a violation inside the *current covenant window*.
        """
        when = when or datetime.utcnow()
        rec = self._get_record(persona_name, window)

        rec.count += 1
        rec.last_violation_at = when
        rec.last_reason = reason

        if rec.first_violation_at is None:
            rec.first_violation_at = when

        return rec

    def get_bottleneck_multiplier(
        self,
        persona_name: str,
        window: AlphaLawWindow,
    ) -> float:
        """
        Compute the risk multiplier for this persona under this covenant window.

        Behavior:

        • If blade_triggered and persona != Alpha → 0.0 (slot sealed)
        • Alpha is never throttled by this counter → 1.0
        • Otherwise violations compress capacity gradually.
        """
        name_lower = persona_name.lower()

        # Blade slot sealing rule
        if window.blade_triggered and name_lower != "alpha":
            return 0.0

        # Alpha is governed by the covenant itself, not by this throttle
        if name_lower == "alpha":
            return 1.0

        rec = self._get_record(persona_name, window)
        c = rec.count
        cfg = self.config

        # Fully allowed
        if c <= cfg.soft_limit_per_window:
            return 1.0

        # Fully muted
        if c >= cfg.hard_limit_per_window:
            return 0.0

        # Linear squeeze between soft and hard limit
        span = cfg.hard_limit_per_window - cfg.soft_limit_per_window
        position = c - cfg.soft_limit_per_window

        return max(
            cfg.min_multiplier,
            1.0 - (1.0 - cfg.min_multiplier) * (position / span),
        )

    # ---------- covenant-window lifecycle ----------

    def reset_window(self, window: AlphaLawWindow) -> None:
        """
        Drop all violation records for this covenant window.

        Called only when Alpha opens a *new covenant window*.
        """
        keys_to_delete = [
            k for k in list(self._records.keys())
            if k[1] == window.covenant_id and k[2] == window.slot_index
        ]
        for k in keys_to_delete:
            del self._records[k]

    def snapshot_window(self, window: AlphaLawWindow) -> Dict[str, WindowViolationRecord]:
        """
        Return all violation records belonging to a single covenant window.
        """
        out: Dict[str, WindowViolationRecord] = {}
        for (persona_name, covenant_id, slot_index), rec in self._records.items():
            if covenant_id == window.covenant_id and slot_index == window.slot_index:
                out[persona_name] = rec
        return out
