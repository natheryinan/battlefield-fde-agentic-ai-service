from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List


def _stable_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


@dataclass
class DecisionLog:
    records: List[Dict[str, Any]] = field(default_factory=list)

    def record(
        self,
        actor_id: str,
        action: str,
        policy_id: str,
        payload: Dict[str, Any],
    ) -> str:
        """
        Append an irreversible record and return decision_hash.
        """
        ts = int(time.time())
        body = {
            "ts": ts,
            "actor_id": actor_id,
            "action": action,
            "policy_id": policy_id,
            "payload": payload,
        }
        digest = hashlib.sha256(_stable_json(body).encode("utf-8")).hexdigest()
        body["decision_hash"] = digest
        self.records.append(body)
        return digest
