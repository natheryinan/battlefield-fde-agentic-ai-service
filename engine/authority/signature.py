from __future__ import annotations

import hmac
import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict


SIGN_DOMAIN = "FDE:AUTHZ:v1"


def _stable_json(obj: Dict[str, Any]) -> bytes:
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _message(*, actor_id: str, payload: Dict[str, Any]) -> bytes:
    # Bind actor_id + domain into the signed material to prevent substitution / cross-context replay.
    envelope = {
        "domain": SIGN_DOMAIN,
        "actor_id": actor_id,
        "payload": payload,
    }
    return _stable_json(envelope)


@dataclass(frozen=True)
class AlphaSignature:
    actor_id: str
    sig: str  # hex digest

    @staticmethod
    def sign(*, actor_id: str, secret: str, payload: Dict[str, Any]) -> "AlphaSignature":
        msg = _message(actor_id=actor_id, payload=payload)
        digest = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()
        return AlphaSignature(actor_id=actor_id, sig=digest)

    @staticmethod
    def verify(*, secret: str, payload: Dict[str, Any], signature: "AlphaSignature") -> bool:
        msg = _message(actor_id=signature.actor_id, payload=payload)
        expected = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature.sig)
