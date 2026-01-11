from __future__ import annotations

import hmac
import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict


def _stable_json(payload: Dict[str, Any]) -> bytes:
    # Stable encoding prevents signature mismatch across runs.
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


@dataclass(frozen=True)
class AlphaSignature:
    actor_id: str
    sig: str  # hex digest

    @staticmethod
    def sign(*, actor_id: str, secret: str, payload: Dict[str, Any]) -> "AlphaSignature":
        msg = _stable_json(payload)
        digest = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()
        return AlphaSignature(actor_id=actor_id, sig=digest)

    @staticmethod
    def verify(*, secret: str, payload: Dict[str, Any], signature: "AlphaSignature") -> bool:
        expected = AlphaSignature.sign(actor_id=signature.actor_id, secret=secret, payload=payload).sig
        return hmac.compare_digest(expected, signature.sig)
