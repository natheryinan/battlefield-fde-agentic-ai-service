from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Optional


@dataclass(frozen=True)
class KeyMaterial:
    pubkey_pem: str
    source: str  # ENV / FILE / KV


def load_pubkey_pem(
    *, env_var: str = "FDE_ALPHA_PUBKEY_PEM",
    file_path_env: str = "FDE_ALPHA_PUBKEY_PATH",
    kv: Optional[object] = None,
    kv_key: str = "alpha:pubkey_pem",
) -> KeyMaterial:
    pem = os.getenv(env_var)
    if pem and pem.strip():
        return KeyMaterial(pubkey_pem=pem.strip(), source="ENV")


    path = os.getenv(file_path_env) or os.path.join(".secrets", "alpha_pubkey.pem")

    if path and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return KeyMaterial(pubkey_pem=f.read().strip(), source="FILE")

    if kv is not None and hasattr(kv, "get"):
        pem = kv.get(kv_key)
        if pem and str(pem).strip():
            return KeyMaterial(pubkey_pem=str(pem).strip(), source="KV")


    raise ValueError("Alpha pubkey PEM missing (ENV/FILE/KV all empty).")


from dataclasses import dataclass
from hashlib import sha256


@dataclass(frozen=True)
class KeyAudit:
    suite: str
    pubkey_present: bool
    pubkey_fp_tag4: str
    source: str


def audit_key_material(km: KeyMaterial, *, suite: str = "FDE-SHAKE256-512-V1") -> KeyAudit:
    raw = km.pubkey_pem.encode("utf-8")
    fp = sha256(raw).hexdigest()  # 今日先用 sha256 做 tag；你要的 C(XOF) 之后可替换
    tag4 = "-".join([fp[i:i + 8] for i in range(0, 32, 8)])
    return KeyAudit(
        suite=suite,
        pubkey_present=bool(km.pubkey_pem),
        pubkey_fp_tag4=tag4,
        source=km.source,
    )
