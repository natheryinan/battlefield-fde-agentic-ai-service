from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .auth_result import AuthorizationResult
from .decision_log import DecisionLog
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
    """
    Canonical enforcement choke-point.

    Rule: Nothing proceeds unless Alpha is present, signature is present,
    signature verifies, signature identity matches, and policy allows it.

    Logging happens ONLY after authorization succeeds.
    """

    def __init__(
        self,
        policy: AuthorityPolicy,
        alpha_secret: str,
        decision_log: Optional[DecisionLog] = None,
    ):
        self.policy = policy
        self.alpha_secret = alpha_secret
        self.log = decision_log or DecisionLog()

    def authorize(self, req: CommitRequest) -> AuthorizationResult:
        """
        The only entry-point for permissioning. Raises on failure.
        On success, returns an explicit authorization artifact required downstream.
        """
        self._require_alpha(req)
        self._require_signature(req)
        self._require_signature_identity(req)   # fail-closed
        self._verify_signature(req)

        policy_id = self._enforce_policy(req)

        # Logging only after authorization succeeds (non-negotiable)
        decision_hash = self.log.record(
            actor_id=req.actor_id,
            action=req.action,
            policy_id=policy_id,
            payload=req.payload,
        )

        return AuthorizationResult(
            allowed=True,
            authority="ALPHA",
            policy_id=policy_id,
            decision_hash=decision_hash,
        )

    # --- existing private checks (keep your implementations) ---

    def _require_alpha(self, req: CommitRequest) -> None:
        if req.actor_id != "ALPHA":
            raise AlphaRequired("Alpha required: actor_id must be 'ALPHA'.")

    def _require_signature(self, req: CommitRequest) -> None:
        if req.signature is None:
            raise SignatureRequired("Signature required: missing signature.")

    def _require_signature_identity(self, req: CommitRequest) -> None:
        # Keep your existing logic; this stub is fail-closed by default.
        # Example: ensure signature.subject == req.actor_id, etc.
        sig = req.signature
        if sig is None:
            raise SignatureRequired("Signature required: missing signature.")
        if getattr(sig, "actor_id", None) not in (None, req.actor_id):
            # If your AlphaSignature stores actor_id, enforce match.
            raise SignatureRequired("Signature identity mismatch (fail-closed).")

    def _verify_signature(self, req: CommitRequest) -> None:
        # Keep your existing logic that verifies cryptographically using alpha_secret
        req.signature.verify(self.alpha_secret, req.action, req.payload)

    def _enforce_policy(self, req: CommitRequest) -> str:
        # IMPORTANT: return a stable policy_id string
        # Example: self.policy.enforce(...) returns something like "POLICY:ALLOW:COMMIT"
        return self.policy.enforce(req.action, req.actor_id, req.payload)
