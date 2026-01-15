# engine/authority/policy.py
from __future__ import annotations

from typing import Any, Dict


class AuthorityPolicy:
    """
    Sovereign rules layer.

    Responsibilities:
      - Define who is Alpha
      - Decide whether an action is allowed (given actor + payload)
      - Provide a policy version string (for evidence logs)
    """

    version: str = "0"

    def is_alpha(self, actor_id: str) -> bool:
        raise NotImplementedError

    def allow(self, action: str, actor_id: str, payload: Dict[str, Any]) -> bool:
        raise NotImplementedError


class StrictAlphaPolicy(AuthorityPolicy):
    """
    STRICT-ALPHA ENFORCEMENT (NON-NEGOTIABLE)

    Rule:
      - Only Alpha is permitted to authorize any action.
      - Non-Alpha actors are denied for every action, without exception.
      - This policy does not "degrade" or "fallback" to lesser authority.

    This is a hard sovereign constraint: if you are not Alpha, you do not pass.
    """

    def __init__(self, alpha_actor_id: str, version: str = "strict-alpha/1") -> None:
        self._alpha_actor_id = alpha_actor_id
        self.version = version

    def is_alpha(self, actor_id: str) -> bool:
        return actor_id == self._alpha_actor_id

    def allow(self, action: str, actor_id: str, payload: Dict[str, Any]) -> bool:
        # HARD RULE: Only Alpha passes. Everyone else is denied.
        return self.is_alpha(actor_id)

