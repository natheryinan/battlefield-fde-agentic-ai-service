from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class MarketState:
    timestamp: Any
    features: Dict[str, float]
    positions: Dict[str, float]
    cash: float
    meta: Dict[str, Any] | None = None

class BasePersona(ABC):
    name: str = "base"

    @abstractmethod
    def act(self, state: MarketState) -> Dict[str, float]:
        """Return action proposal: symbol -> desired delta / weight."""
        raise NotImplementedError

    def update(
        self,
        reward: float,
        next_state: MarketState,
        info: Dict[str, Any] | None = None,
    ) -> None:
        """Optional learning / bookkeeping hook."""
        return
