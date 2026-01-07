# architecture/model/fde_core_spec.py

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Any

from architecture.data.schemas import (
    DecisionRequest,
    DecisionResponse,
    UniverseDefinition,
    RiskLimits,
)


class FDECore(ABC):
    """
    Abstract contract for any FDE core engine implementation.
    """

    def __init__(
        self,
        universe: UniverseDefinition,
        base_risk_limits: RiskLimits,
        config: Dict[str, Any] | None = None,
    ) -> None:
        self.universe = universe
        self.base_risk_limits = base_risk_limits
        self.config: Dict[str, Any] = config or {}

    @abstractmethod
    def decide(self, request: DecisionRequest) -> DecisionResponse:
        """
        Single-step decision function.
        """
        raise NotImplementedError

    @abstractmethod
    def reset(self) -> None:
        """
        Reset internal state before a new experiment / episode.
        """
        raise NotImplementedError

    def update_config(self, **kwargs: Any) -> None:
        """
        Optional reconfiguration hook between episodes.
        """
        self.config.update(kwargs)
