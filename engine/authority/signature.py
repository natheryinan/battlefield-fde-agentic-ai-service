# engine/authority/signature.py
from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Any, Dict, Optional


def _canonical_payload(payload: Dict[str, Any]) -> bytes:
    """
    Stable canonicalization for signing/verifying.
    Ensures deterministic bytes even if dict key order changes.
    """
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


@dataclass(frozen=True)
class AlphaSignature:
    """
    Evidence-grade signature container.

    Identity anchor:
      - pubkey preferred (string)
      - key_id allowed (string)

    Signature material:
      - mac: hex string (HMAC stub)
    """
    mac: str
    pubkey: Optional[str] = None
    key_id: Optional[str] = None

    @staticmethod
    def sign(
        *,
        secret: str,
        action: str,
        payload: Dict[str, Any],
        actor_id: str,
        pubkey: Optional[str] = None,
        key_id: Optional[str] = None,
    ) -> "AlphaSignature":
        msg = AlphaSignature._message_bytes(action=action, payload=payload, actor_id=actor_id)
        mac = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()
        return AlphaSignature(mac=mac, pubkey=pubkey, key_id=key_id)

    def verify(
        self,
        *,
        secret: str,
        action: str,
        payload: Dict[str, Any],
        actor_id: str,
    ) -> bool:
        """
        Verify signature against canonical bytes (HMAC stub).
        Replace internals later with GPG/HSM without changing the interface.
        """
        msg = self._message_bytes(action=action, payload=payload, actor_id=actor_id)
        expected = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()
        return hmac.compare_digest(self.mac, expected)

    def identity_fingerprint(self) -> str:
        """
        Evidence-grade identity fingerprint.
        Prefer pubkey; fallback to key_id.
        """
        if self.pubkey not in (None, ""):
            return "pubkey:" + hashlib.sha256(self.pubkey.encode("utf-8")).hexdigest()
        if self.key_id not in (None, ""):
            return "key_id:" + hashlib.sha256(self.key_id.encode("utf-8")).hexdigest()
        # Gate will fail-closed before this, but keep it hard anyway.
        raise ValueError("Signature identity missing: pubkey or key_id required.")

    def fingerprint(self) -> str:
        """
        Backward-compatible alias.
        """
        return self.identity_fingerprint()

    @staticmethod
    def _message_bytes(*, action: str, payload: Dict[str, Any], actor_id: str) -> bytes:
        # Bind actor_id into the signed message (prevents signature reuse across actors).
        p = _canonical_payload(payload)
        return b"|".join(
            [
                action.encode("utf-8"),
                actor_id.encode("utf-8"),
                p,
            ]
        )
