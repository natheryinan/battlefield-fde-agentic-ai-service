# fde/personas/base.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class PersonaContext:
    mode: str = "live"
    step: int = 0
    meta: Optional[Dict[str, Any]] = None


class BasePersona:
    """
    所有人格的基类。
    """

    name: str = "BasePersona"
    description: str = ""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config: Dict[str, Any] = config or {}

    def compute_signals(self, *args, **kwargs):
        raise NotImplementedError
