# engine/authority/decision_log.py
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class DecisionLog:
    """
    Evidence-grade decision log (append-only style).
    Default: JSONL file in cwd unless log_path is provided.
    """

    log_path: Optional[str] = None

    def __post_init__(self) -> None:
        if self.log_path is None:
            self.log_path = os.path.join(os.getcwd(), "fde_authority_log.jsonl")

    def record_authorized_commit(
        self,
        *,
        actor_id: str,
        action: str,
        payload: Dict[str, Any],
        policy_version: str,
        alpha_fingerprint: str,
    ) -> None:
        event = {
            "ts": int(time.time()),
            "event": "AUTHORIZED_COMMIT",
            "actor_id": actor_id,
            "action": action,
            "payload": payload,
            "policy_version": policy_version,
            "alpha_fingerprint": alpha_fingerprint,
        }
        line = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
        # append-only
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
