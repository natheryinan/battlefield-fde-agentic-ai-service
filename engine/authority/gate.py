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
        self.policy = policy
        self.alpha_secret = alpha_secret

    def require_alpha(self, req: CommitRequest) -> None:
        if req.actor_id != self.policy.alpha_actor_id:
            raise AlphaRequired(
                f"Commit action '{req.action}' requires Alpha actor_id='{self.policy.alpha_actor_id}', got '{req.actor_id}'."
            )

    def require_signature(self, req: CommitRequest) -> None:
        if req.signature is None:
            raise SignatureRequired("Alpha signature is required for commit actions.")

        if req.signature.actor_id != self.policy.alpha_actor_id:
            raise SignatureRequired(f"Signature actor_id must be '{self.policy.alpha_actor_id}'.")

        ok = AlphaSignature.verify(secret=self.alpha_secret, payload=req.payload, signature=req.signature)
        if not ok:
            raise SignatureRequired("Invalid Alpha signature.")

    def authorize(self, req: CommitRequest) -> None:
        """
        Enforce: any commit action => must be Alpha + valid Alpha signature.
        """
        if req.action in self.policy.commit_actions:
            self.require_alpha(req)
            self.require_signature(req)
        # Non-commit actions may pass (advisory outputs, observations, etc.)
