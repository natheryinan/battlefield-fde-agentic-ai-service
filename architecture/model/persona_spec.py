# architecture/model/persona_spec.py

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Any

from architecture.data.schemas import DecisionRequest, DecisionResponse


class Persona(ABC):
    """
    Abstract contract for a single persona.
    """

    def __init__(self, name: str, role: str, weight: float = 1.0) -> None:
        """
        :param name: internal name, e.g. "GUARDIAN", "LIQUIDITY"
        :param role: semantic role description
        :param weight: advisory weight in aggregation logic
        """
        self.name = name.upper()
        self.role = role
        self.weight = weight

    @abstractmethod
    def propose(self, request: DecisionRequest) -> DecisionResponse:
        """
        Produce an advisory decision surface for this persona alone.
        """
        raise NotImplementedError

    def set_weight(self, new_weight: float) -> None:
        self.weight = new_weight

    def extra_state(self) -> Dict[str, Any]:
        """
        Optional debugging / diagnostics state.
        """
        return {}
