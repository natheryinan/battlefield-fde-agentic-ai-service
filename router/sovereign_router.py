"""
Sovereign Router
----------------
Central judge that:

- Reads RegimeAssessment (from RegimeEngine)
- Evaluates persona action proposals
- Enforces regime-aware constraints (leverage / pos change / gross shift)
- Tracks covenant violations with time-aware cooldowns

Concepts:
- CovenantCounter: how many times a persona has tried to cross the line
- TimeRestraint: simple step-based cooldown after hard breach
"""

from dataclasses import dataclass, field
from typing import Dict, Optional

# Adjust this import path to your project structure, e.g.:
# from engine.regime_engine import RegimeAssessment
try:
    from engine.regime_engine import RegimeAssessment
except ImportError:  # type: ignore
    # type stub / fallback for static analysis
    @dataclass
    class RegimeAssessment:  # pragma: no cover
        score: float
        label: str
        band: int
        max_leverage: float
        max_position_change: float
        max_gross_shift: float
        persona_guidance: Dict[str, str]


# ===== Core Action / Decision Types =====================================

@dataclass
class PersonaActionRequest:
    """
    What a persona WANTS to do this step.
    All values are *proposed* deltas or caps before sovereign review.
    """
    persona: str
    proposed_leverage: float
    proposed_position_change: float
    proposed_gross_shift: float
    metadata: Optional[dict] = None   # e.g. symbol, regime snapshot, etc.


@dataclass
class PersonaActionDecision:
    """
    What the SovereignRouter ALLOWS after review.
    """
    persona: str
    approved: bool

    # final allowed values after clamping / override
    allowed_leverage: float
    allowed_position_change: float
    allowed_gross_shift: float

    # explanation + covenant tracking
    reason: str
    covenant_violations_after: int
    under_cooldown: bool


# ===== Covenant & Time Restraint Objects ================================

@dataclass
class CovenantCounter:
    """
    Tracks how many times a persona pushed beyond covenant limits.
    """
    violations: int = 0
    hard_lock: bool = False   # once True, persona is legally frozen until reset

    def increment(self):
        self.violations += 1

    def lock(self):
        self.hard_lock = True

    def reset(self):
        self.violations = 0
        self.hard_lock = False


@dataclass
class TimeRestraint:
    """
    Simple step-index based cooldown.

    cooling_until_step:
        if current_step < cooling_until_step => persona is still cooling down
    """
    cooling_until_step: Optional[int] = None

    def is_active(self, current_step: int) -> bool:
        return (
            self.cooling_until_step is not None
            and current_step < self.cooling_until_step
        )

    def start(self, current_step: int, cooldown_span: int):
        self.cooling_until_step = current_step + max(cooldown_span, 1)

    def clear(self):
        self.cooling_until_step = None


# ===== SovereignRouter ==================================================

@dataclass
class SovereignRouterConfig:
    """
    Global config for the router's legal + temporal restraints.
    """
    max_violations_before_lock: int = 1      # "blade once, then no more"
    cooldown_steps_after_violation: int = 50 # how many steps to cool
    guardian_persona_name: str = "GUARDIAN"  # who enforces the lock


@dataclass
class SovereignRouterState:
    """
    Mutable state of the router across steps.
    """
    step_index: int = 0
    covenant_counters: Dict[str, CovenantCounter] = field(default_factory=dict)
    time_restraints: Dict[str, TimeRestraint] = field(default_factory=dict)

    def ensure_persona(self, persona: str):
        if persona not in self.covenant_counters:
            self.covenant_counters[persona] = CovenantCounter()
        if persona not in self.time_restraints:
            self.time_restraints[persona] = TimeRestraint()


class SovereignRouter:
    """
    The top-level router that:

    - Reads RegimeAssessment
    - Receives PersonaActionRequest
    - Returns PersonaActionDecision

    It does NOT generate trades itself; it just sets the legal corridor.
    """

    def __init__(self, config: Optional[SovereignRouterConfig] = None):
        self.config = config or SovereignRouterConfig()
        self.state = SovereignRouterState()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def advance_step(self):
        """Call once per decision step."""
        self.state.step_index += 1

    def evaluate_action(
        self,
        assessment: RegimeAssessment,
        action: PersonaActionRequest,
    ) -> PersonaActionDecision:
    
        persona = action.persona.upper()
        self.state.ensure_persona(persona)

        c = self.state.covenant_counters[persona]
        t = self.state.time_restraints[persona]

        # 1. If persona is under hard legal lock, nothing passes.
        if c.hard_lock:
            return PersonaActionDecision(
                persona=persona,
                approved=False,
                allowed_leverage=0.0,
                allowed_position_change=0.0,
                allowed_gross_shift=0.0,
                reason=(
                    "Persona locked by covenant: prior breach exceeded "
                    "allowed violation limit."
                ),
                covenant_violations_after=c.violations,
                under_cooldown=True,
            )

        # 2. Time-based cooldown
        if t.is_active(self.state.step_index):
            return PersonaActionDecision(
                persona=persona,
                approved=False,
                allowed_leverage=0.0,
                allowed_position_change=0.0,
                allowed_gross_shift=0.0,
                reason="Persona cooling down; time restraint still active.",
                covenant_violations_after=c.violations,
                under_cooldown=True,
            )

        # 3. Regime-aware HARD CAPS
        max_lev = assessment.max_leverage
        max_pos = assessment.max_position_change
        max_gross = assessment.max_gross_shift

        # clamp proposals to legal corridor
        final_lev = min(action.proposed_leverage, max_lev)
        final_pos = min(abs(action.proposed_position_change), max_pos)
        final_gross = min(abs(action.proposed_gross_shift), max_gross)

        # 4. Check if clamping was necessary (breach attempt)
        breach_attempt = (
            action.proposed_leverage > max_lev
            or abs(action.proposed_position_change) > max_pos
            or abs(action.proposed_gross_shift) > max_gross
        )

        reason_parts = []
        if breach_attempt:
            c.increment()
            # Start cooldown
            t.start(
                current_step=self.state.step_index,
                cooldown_span=self.config.cooldown_steps_after_violation,
            )
            reason_parts.append(
                "Proposal exceeded regime corridor; action clamped and cooldown started."
            )

            # If violations exceed limit, lock this persona
            if c.violations > self.config.max_violations_before_lock:
                c.lock()
                reason_parts.append(
                    "Covenant limit crossed: persona moved into hard lock."
                )
        else:
            reason_parts.append("Within regime corridor; action approved as-is.")

        # 5. Persona-specific guidance from assessment (optional, cosmetic)
        persona_guidance = assessment.persona_guidance.get(persona, "")
        if persona_guidance:
            reason_parts.append(f"Guidance: {persona_guidance}")

        approved = not c.hard_lock and not t.is_active(self.state.step_index)

        return PersonaActionDecision(
            persona=persona,
            approved=approved,
            allowed_leverage=final_lev if approved else 0.0,
            allowed_position_change=final_pos if approved else 0.0,
            allowed_gross_shift=final_gross if approved else 0.0,
            reason(" ".join(reason_parts)),
            covenant_violations_after=c.violations,
            under_cooldown=t.is_active(self.state.step_index),
        )
