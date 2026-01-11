
from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet


@dataclass(frozen=True)
class AuthorityPolicy:
    """
    Canonical authority rules for the system.
    Keep this *small* and treat it as law.
    """
    alpha_actor_id: str = "ALPHA"
    commit_actions: FrozenSet[str] = frozenset({
        "STATE_MUTATE",
        "ORDER_PLACE",
        "POSITION_CHANGE",
        "RISK_ENVELOPE_CHANGE",
        "REGIME_LOCK",
        "CONFIG_WRITE",
        "DECISION_COMMIT",
    })

    # Personas that may advise but can never commit.
    advisory_personas: FrozenSet[str] = frozenset({
        "ADVISOR",
        "GUARDIAN",
        "SENTINEL",
        "AUDITOR",
        "SCOUT",
    })
