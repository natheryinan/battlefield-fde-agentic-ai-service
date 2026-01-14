from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Mapping

from .errors import AlphaRequired, SignatureRequired
from .policy import AuthorityPolicy
from .signature import AlphaSignature
from engine.authority.decision_log import DecisionLog




@dataclass(frozen=True)
class CommitRequest:
    
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
        Enforce: any commit action => must be Alpha + valid Alpha signature.
        """
        if req.action in self.policy.commit_actions:
            self.require_alpha(req)
            self.require_signature(req)
        def is_advisory_allowed(self, action: str) -> bool:
        """
        Non-commit actions must be explicitly allowed.
        Default deny if unknown.
        """
        return action in getattr(self.policy, "advisory_actions", set())

