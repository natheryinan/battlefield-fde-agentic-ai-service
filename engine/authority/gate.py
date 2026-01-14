from .errors import AlphaRequired, SignatureRequired, NotAuthorized
from engine.authority.decision_log import DecisionLog


from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .errors import AlphaRequired, SignatureRequired
from .policy import AuthorityPolicy
from .signature import AlphaSignature


@dataclass(frozen=True)
class CommitRequest:
    action: str
    actor_id: str
    payload: Dict[str, Any]
    signature: Optional[AlphaSignature] = None


class AuthorityGate:
    def __init__(self, policy: AuthorityPolicy, alpha_secret: str):
        if not policy.alpha_actor_id:
            raise ValueError("AuthorityPolicy.alpha_actor_id must be defined.")
        if not policy.commit_actions:
            raise ValueError("AuthorityPolicy.commit_actions must not be empty.")
        if not alpha_secret:
            raise ValueError("alpha_secret must be provided for Alpha verification.")

        self.policy = policy
        self.alpha_secret = alpha_secret

    def authorize(self, req: CommitRequest) -> None:
    """
    Enforce:
      - commit actions => must be Alpha + valid Alpha signature
      - non-commit actions => must be explicitly allowed (default deny)
    Always audit ALLOW/DENY via DecisionLog.
    """
    try:
        if req.action in self.policy.commit_actions:
            self.require_alpha(req)
            self.require_signature(req)

            # ✅ A: audit allow
            self._audit(req, outcome="ALLOW", reason="commit action authorized")
            return

        if not self.is_advisory_allowed(req.action):
            raise NotAuthorized(f"Action not allowed: {req.action}")

        # ✅ A: audit allow
        self._audit(req, outcome="ALLOW", reason="advisory action allowed")
        return

    except Exception as e:
        # ✅ A: audit deny (capture reason)
        self._audit(req, outcome="DENY", reason=f"{type(e).__name__}: {e}")
        raise

    def is_advisory_allowed(self, action: str) -> bool:
        """
        Non-commit actions must be explicitly allowed.
        Default deny if unknown.
        """
        advisory = getattr(self.policy, "advisory_actions", set())
        return action in advisory

    def require_alpha(self, req: CommitRequest) -> None:
        if req.actor_id != self.policy.alpha_actor_id:
            raise AlphaRequired("Alpha authority required for this action.")

    def require_signature(self, req: CommitRequest) -> None:
        if req.signature is None:
            raise SignatureRequired("Alpha signature required for commit action.")

        # bind actor_id identity
        if req.signature.actor_id != req.actor_id:
            raise SignatureRequired("Signature actor_id mismatch.")

        if not AlphaSignature.verify(
            secret=self.alpha_secret,
            payload=req.payload,
            signature=req.signature,
        ):
            raise SignatureRequired("Invalid Alpha signature.")
