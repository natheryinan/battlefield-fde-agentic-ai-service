from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from .base import PersonaOutput


@dataclass
class AdvisorPersona:
    actor_id: str = "ADVISOR"
    role: str = "ADVISORY_ONLY"

    def think(self, context: Dict[str, Any]) -> PersonaOutput:
        # Produce advice only. Never a commit.
        return PersonaOutput(
            actor_id=self.actor_id,
            kind="ADVICE",
            payload={
                "note": "Suggestions based on signals. Non-binding.",
                "context_digest": context.get("digest"),
            },
        )
