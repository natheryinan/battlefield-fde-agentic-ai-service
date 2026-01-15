# engine/authority/types.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .signature import AlphaSignature


@dataclass(frozen=True)
class CommitRequest:
    action: str
    actor_id: str
    payload: Dict[str, Any]
    signature: Optional[AlphaSignature] = None
