# fde/engine/gates/execution_gate.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


@dataclass(frozen=True)
class GateDecision:
    allowed: bool
    reason: str
    metadata: Dict[str, Any]


class ExecutionGate:
    """
    Front-up veto gate.
    Runs BEFORE any action is executed (before orders, before on-chain signing, before commits).
    """

    def evaluate(
        self,
        *,
        regime: Dict[str, Any],
        decision: Dict[str, Any],
        guardian: Optional[Any] = None,
    ) -> GateDecision:
        # 1) Regime-based hard constraints (irreversibility, rollback forbidden, etc.)
        irreversible = bool(regime.get("irreversible", False))
        rollback_allowed = bool(regime.get("rollback_allowed", True))

        expected_loss = decision.get("expected_loss", "unknown")  # e.g., low/medium/high
        uncertainty = decision.get("estimated_uncertainty", "unknown")  # low/medium/high

        # Hard rule: if irreversible but rollback_allowed==True => configuration conflict => block
        if irreversible and rollback_allowed:
            return GateDecision(
                allowed=False,
                reason="gate_block: invalid_regime_conflict (irreversible=true but rollback_allowed=true)",
                metadata={"irreversible": irreversible, "rollback_allowed": rollback_allowed},
            )

        # Hard rule: irreversible + expected_loss high => block (front-up veto)
        if irreversible and expected_loss in ("high", "very_high", True):
            return GateDecision(
                allowed=False,
                reason="gate_veto: guardian_preemptive_veto (irreversible + high_expected_loss)",
                metadata={"irreversible": irreversible, "expected_loss": expected_loss},
            )

        # 2) Optional Guardian hook (policy can be more nuanced)
        if guardian is not None and hasattr(guardian, "pre_execution_veto"):
            veto, veto_reason, veto_meta = guardian.pre_execution_veto(regime=regime, decision=decision)
            if veto:
                return GateDecision(
                    allowed=False,
                    reason=f"gate_veto: {veto_reason}",
                    metadata={"guardian": True, **(veto_meta or {})},
                )

        # Otherwise allow
        return GateDecision(
            allowed=True,
            reason="gate_allow: passed_pre_execution_checks",
            metadata={"irreversible": irreversible, "expected_loss": expected_loss, "uncertainty": uncertainty},
        )
