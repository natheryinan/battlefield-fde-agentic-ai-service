# engine/authority/gate.py
from __future__ import annotations

from typing import Optional

from .decision_log import DecisionLog
from .errors import AlphaRequired, PolicyDenied, SignatureRequired
from .policy import AuthorityPolicy
from .signature import AlphaSignature
from .types import CommitRequest


class AuthorityGate:
    """
    Canonical enforcement choke-point.

    Rule: Nothing proceeds unless Alpha is present, signature is present,
    signature binds to a stable identity anchor, signature verifies, and policy allows it.

    Logging happens ONLY after authorization succeeds.
    """

    def __init__(
        self,
        policy: AuthorityPolicy,
        alpha_secret: str,
        decision_log: Optional[DecisionLog] = None,
    ) -> None:
        self.policy = policy
        self.alpha_secret = alpha_secret
        self.log = decision_log or DecisionLog()

    def authorize(self, req: CommitRequest) -> None:
        """
        The only entry-point for permissioning. Raises on failure.
        """
        self._require_alpha(req)
        self._require_signature(req)
        self._require_signature_identity(req)   # fail closed
        self._verify_signature(req)
        self._enforce_policy(req)

        sig = req.signature
        assert sig is not None  # for type-checkers / invariants

        # Evidence-grade log occurs ONLY after success.
        self.log.record_authorized_commit(
            actor_id=req.actor_id,
            action=req.action,
            payload=req.payload,
            policy_version=self._policy_version(),
            alpha_fingerprint=self._alpha_fingerprint(sig),
        )

    # -----------------------
    # Preconditions (fail-closed)
    # -----------------------

    def _require_alpha(self, req: CommitRequest) -> None:
        if not self.policy.is_alpha(req.actor_id):
            raise AlphaRequired(
                f"Alpha required. actor_id={req.actor_id!r} is not Alpha."
            )

    def _require_signature(self, req: CommitRequest) -> None:
        if req.signature is None:
            raise SignatureRequired(
                f"Signature required for action={req.action!r}."
            )

    def _require_signature_identity(self, req: CommitRequest) -> None:
        """
        Evidence-grade requirement:
        signature must bind to a stable identity anchor (pubkey preferred, or key_id).
        If both are missing/None/empty, FAIL CLOSED.
        """
        sig = req.signature
        if sig is None:
            raise SignatureRequired("Signature required.")

        pubkey = getattr(sig, "pubkey", None)
        key_id = getattr(sig, "key_id", None)

        if pubkey in (None, "") and key_id in (None, ""):
            raise SignatureRequired(
                "Signature identity missing: pubkey (preferred) or key_id required."
            )

    def _verify_signature(self, req: CommitRequest) -> None:
        sig = req.signature
        if sig is None:
            raise SignatureRequired("Signature required.")

        ok = sig.verify(
            secret=self.alpha_secret,
            action=req.action,
            payload=req.payload,
            actor_id=req.actor_id,  # bind identity into signature check
        )
        if not ok:
            raise SignatureRequired("Invalid AlphaSignature. Authorization denied.")

    def _enforce_policy(self, req: CommitRequest) -> None:
        allowed = self.policy.allow(
            action=req.action,
            actor_id=req.actor_id,
            payload=req.payload,
        )
        if not allowed:
            raise PolicyDenied(
                f"Policy denied action={req.action!r} for actor_id={req.actor_id!r}."
            )

    # -----------------------
    # Evidence helpers
    # -----------------------

    def _policy_version(self) -> str:
        v = getattr(self.policy, "version", None)
        return str(v) if v is not None else "unknown"

    def _alpha_fingerprint(self, sig: AlphaSignature) -> str:
        """
        Evidence-grade fingerprint.
        Prefer identity_fingerprint() if present; otherwise fallback to fingerprint().
        """
        ident_fp = getattr(sig, "identity_fingerprint", None)
        if callable(ident_fp):
            return str(ident_fp())

        fp = getattr(sig, "fingerprint", None)
        if callable(fp):
            return str(fp())

        raise SignatureRequired(
            "AlphaSignature must implement identity_fingerprint() "
            "or fingerprint() for evidence logging."
        )
