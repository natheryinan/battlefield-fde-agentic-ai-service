
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


def _stable_json(obj: Dict[str, Any]) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class DecisionRecord:
    ts: float
    action: str
    actor_id: str
    payload: Dict[str, Any]
    signature_hex: str
    prev_hash: str
    record_hash: str

    @staticmethod
    def create(
        *,
        action: str,
        actor_id: str,
        payload: Dict[str, Any],
        signature_hex: str,
        prev_hash: str,
        ts: Optional[float] = None,
    ) -> "DecisionRecord":
        ts = time.time() if ts is None else ts
        base = {
            "ts": ts,
            "action": action,
            "actor_id": actor_id,
            "payload": payload,
            "signature_hex": signature_hex,
            "prev_hash": prev_hash,
        }
        record_hash = _sha256(_stable_json(base))
        return DecisionRecord(
            ts=ts,
            action=action,
            actor_id=actor_id,
            payload=payload,
            signature_hex=signature_hex,
            prev_hash=prev_hash,
            record_hash=record_hash,
        )


class DecisionLog:
    """
    In-memory implementation. Later you can persist to disk, DB, KV, etc.
    """
    def __init__(self) -> None:
        self._records: List[DecisionRecord] = []
        self._genesis_hash = "0" * 64

    @property
    def last_hash(self) -> str:
        return self._records[-1].record_hash if self._records else self._genesis_hash

    def append(self, record: DecisionRecord) -> None:
        self._records.append(record)

    def verify_chain(self) -> bool:
        prev = self._genesis_hash
        for r in self._records:
            base = {
                "ts": r.ts,
                "action": r.action,
                "actor_id": r.actor_id,
                "payload": r.payload,
                "signature_hex": r.signature_hex,
                "prev_hash": r.prev_hash,
            }
            expected_hash = _sha256(_stable_json(base))
            if r.prev_hash != prev:
                return False
            if r.record_hash != expected_hash:
                return False
            prev = r.record_hash
        return True
