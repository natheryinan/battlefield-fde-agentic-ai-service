from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict


FDE_HASH_SUITE = "FDE-SHAKE256-512-V1"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_json(obj: Any) -> str:
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def to_bytes(x: Any) -> bytes:
    if isinstance(x, bytes):
        return x
    if isinstance(x, str):
        return x.encode("utf-8")
    raise TypeError("Expected bytes or str.")


def shake256_hex(domain: str, payload: bytes, out_bytes: int) -> str:
    """
    Domain-separated XOF hash: SHAKE256(domain || 0x00 || payload).
    Returns hex string of length out_bytes*2.
    """
    h = hashlib.shake_256()
    h.update(domain.encode("utf-8"))
    h.update(b"\x00")
    h.update(payload)
    return h.hexdigest(out_bytes)


def canonical_dict(obj: Any, fallback: Dict[str, Any]) -> Dict[str, Any]:
    if is_dataclass(obj):
        d = asdict(obj)
    else:
        d = fallback
    return {k: v for k, v in d.items() if v is not None}
