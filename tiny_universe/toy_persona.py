

from __future__ import annotations

from typing import Any
import numpy as np
import pandas as pd


class ToyAlphaPersona:
    
    name = "Toy-Alpha"

    def __init__(self, lookback: int = 60) -> None:
        
        self.lookback = int(lookback)

    def compute_signals(
        self,
        snapshot: Any,
        portfolio: Any,
        ctx: Any,
        **kwargs: Any,
    ) -> pd.Series:
      
        prices = snapshot.prices.astype(float)

        mean = prices.mean()
        std = prices.std(ddof=0) or 1.0
        z = (prices - mean) / std

        return z.clip(-3, 3)


class ToyConvexityPersona:
   
    name = "Toy-Convexity"

    def compute_signals(
        self,
        snapshot: Any,
        portfolio: Any,
        ctx: Any,
        **kwargs: Any,
    ) -> pd.Series:
        prices = snapshot.prices.astype(float)

        
        rel = prices / prices.mean() - 1.0
        conv = rel ** 2

        if conv.std(ddof=0) == 0:
            return conv * 0.0

        conv = (conv - conv.mean()) / conv.std(ddof=0)
        return conv.clip(-3, 3)


class ToyGuardianPersona:
    
    name = "Toy-Guardian"

    def compute_signals(
        self,
        snapshot: Any,
        portfolio: Any,
        ctx: Any,
        **kwargs: Any,
    ) -> pd.Series:
        prices = snapshot.prices.astype(float)

        
        if getattr(portfolio, "positions", None) is None:
            pos = pd.Series(0.0, index=prices.index)
        else:
            pos = portfolio.positions.reindex(prices.index).fillna(0.0).astype(float)

        risk_score = -pos.abs()

        if risk_score.std(ddof=0) == 0:
            return risk_score * 0.0

        risk_score = (risk_score - risk_score.mean()) / risk_score.std(ddof=0)
        return risk_score.clip(-3, 3)


__all__ = [
    "ToyAlphaPersona",
    "ToyConvexityPersona",
    "ToyGuardianPersona",
]
