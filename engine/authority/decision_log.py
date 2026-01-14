"""
Sovereign Decision Log
=====================

This module records irreversible and reversible decisions
authorized by Alpha and enforced by Guardian.

This is NOT a debug log.
This is a sovereign decision record.
"""

from datetime import datetime
from typing import Any, Dict, Optional


class DecisionLog:
    """
    Records decisions as sovereign actions.
    Each record is immutable once sealed.
    """

    def __init__(self) -> None:
        self._records = []

    def record(
        self,
        *,
        decision_authority: str,
        enforcement_layer: str,
        scope: str,
        regime: str,
        trigger: str,
        decision: str,
        cost_owner: str,
        violated_constraints: Optional[list[str]] = None,
        rollback_allowed: bool = False,
    ) -> Dict[str, Any]:
        """
        Create a sovereign decision record.

        cost_owner:
            The executor or actor who bears the full cost
            of this decision and its consequences.
        """

        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "authority": {
                "decision_authority": decision_authority,
                "enforcement_layer": enforcement_layer,
                "scope": scope,  # IRREVERSIBLE | REVERSIBLE
            },
            "context": {
                "regime": regime,
                "trigger": trigger,
                "violated_constraints": violated_constraints or [],
            },
            "outcome": {
                "decision": decision,
                "cost_owner": cost_owner,
                "rollback_allowed": rollback_allowed,
            },
            "sealed": True,
        }

        self._records.append(record)
        return record

    def all_records(self) -> list[Dict[str, Any]]:
        """
        Return all decision records.
        Records are append-only.
        """
        return list(self._records)
