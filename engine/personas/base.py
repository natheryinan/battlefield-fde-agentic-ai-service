from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Protocol


@dataclass(frozen=True)
class PersonaOutput:
    actor_id: str
    kind: str  # "ADVICE" | "ALERT" | "OBSERVATION" | "DECISION"
    payload: Dict[str, Any]


class Persona(Protocol):
    actor_id: str
    role: str

    def think(self, context: Dict[str, Any]) -> PersonaOutput: ...
