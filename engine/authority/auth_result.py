from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AuthorizationResult:
    """
    Explicit authorization artifact.

    Downstream execution MUST require this object. Absence = no authority.
    """
    allowed: bool
    authority: str          # e.g., "ALPHA"
    policy_id: str          # stable identifier from policy enforcement
    decision_hash: str      # irreversible trace recorded post-authorization
