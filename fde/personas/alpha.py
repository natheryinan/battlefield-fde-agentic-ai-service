# fde/personas/alpha.py
from __future__ import annotations
import numpy as np
import pandas as pd
from typing import Dict, Any

from fde.personas.base import BasePersona, PersonaContext
from fde.interfaces.market import MarketSnapshot
from fde.interfaces.risk import PortfolioState


class AlphaPersona(BasePersona):
    """
    FDE-Alpha V3 (SP500 Factors)
    ------------------------------------
    This version uses *actual* S&P500 trading factors:
      - Momentum (12-1)
      - Reversal (5D)
      - Size (market cap log)
      - Volatility (20D realized)
      - Beta vs SPX
      - Value (B/M)
      - Quality (ROE)
      - Liquidity (ADV)
    """

    name = "FDE-Alpha"
    description = "SP500 multi-factor, market-neutral stat-arb persona."

    def __init__(self, config: Dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self.clip_z = float(self.config.get("clip_z", 3.0))
        self.ema_alpha = float(self.config.get("ema_alpha", 0.25))
        self.target_vol = float(self.config.get("target_vol", 0.20))
        self.prev_signal = None

    # -------------- zscore --------------
    @staticmethod
    def _z(x: pd.Series) -> pd.Series:
        return (x - x.mean()) / (x.std() + 1e-8)

    # -------------- Build SP500 Factors --------------
    def _compute_sp500_factors(
        self,
        snapshot: MarketSnapshot,
        history: pd.DataFrame | None,
    ) -> pd.DataFrame:

        prices = snapshot.prices

        # history format: MultiIndex (date, symbol) with fields:
        # ['close', 'mcap', 'bm', 'roe', 'volume']
        if history is None:
            raise RuntimeError("SP500 factors require historical panel data")

        # Pivot into wide form for easier operations
        close = history['close'].unstack()
        mcap = history['mcap'].unstack()
        bm   = history['bm'].unstack()
        roe  = history['roe'].unstack()
        volume = history['volume'].unstack()

        # -------- 1. MOMENTUM (12-1) --------
        mom = (close.shift(1) / close.shift(252) - 1).iloc[-1]

        # -------- 2. REVERSAL (5D) ----------
        rev = -(close.iloc[-1] / close.iloc[-6] - 1)

        # -------- 3. SIZE --------------------
        size = np.log(mcap.iloc[-1])

        # -------- 4. VOLATILITY (20D) --------
        returns = close.pct_change()
        vol20 = returns.rolling(20).std().iloc[-1] * np.sqrt(252)

        # -------- 5. BETA vs SPX -------------
        spx_ret = returns['SPY'] if 'SPY' in returns.columns else returns.mean(axis=1)

        cov = returns.rolling(60).cov(spx_ret).iloc[-1]
        var = spx_ret.rolling(60).var().iloc[-1]
        beta = cov / (var + 1e-12)

        # -------- 6. VALUE (B/M) -------------
        value = np.log(bm.iloc[-1])

        # -------- 7. QUALITY (ROE) -----------
        quality = roe.iloc[-1]

        # -------- 8. LIQUIDITY (ADV20) -------
        adv20 = volume.rolling(20).mean().iloc[-1]
        liquidity = np.log(adv20 + 1)

        # -------- Assemble factor table -------
        factors = pd.DataFrame({
            "mom12_1": mom,
            "rev5d": rev,
            "size": size,
            "vol20": vol20,
            "beta": beta,
            "value": value,
            "quality": quality,
            "liquidity": liquidity,
        }).reindex(prices.index)

        return factors

    # -------------- Combine Factors --------------
    def _combine_factors(self, fac: pd.DataFrame) -> pd.Series:
        # Equal-weight or configurable weights
        weights = {
            "mom12_1":  1.0,
            "rev5d":    1.0,
            "size":     0.5,
            "vol20":    -0.5,   # lower vol preferred
            "beta":     -0.5,   # lower beta preferred for neutral strategies
            "value":    1.0,
            "quality":  1.0,
            "liquidity": 0.5,
        }

        alpha = pd.Series(0.0, index=fac.index)

        for k, w in weights.items():
            if k in fac.columns:
                alpha += w * self._z(fac[k])

        return alpha

    # -------------- Stabilize + Clip + Normalize --------------
    def _post_process(self, alpha: pd.Series) -> pd.Series:
        clipped = alpha.clip(-self.clip_z, self.clip_z)

        if self.prev_signal is None:
            smoothed = clipped
        else:
            smoothed = (
                self.ema_alpha * clipped
                + (1 - self.ema_alpha) * self.prev_signal
            )

        self.prev_signal = smoothed

        # final normalize to target vol
        vol = smoothed.std()
        if vol < 1e-8:
            return smoothed * 0
        return smoothed * (self.target_vol / vol)

    # -------------- MAIN --------------
    def compute_signals(
        self,
        snapshot: MarketSnapshot,
        portfolio: PortfolioState,
        ctx: PersonaContext,
    ) -> pd.Series:

        # historical panel data must be passed via snapshot.features["history"]
        history = None
        if snapshot.features is not None:
            history = snapshot.features.get("history")

        factors = self._compute_sp500_factors(snapshot, history)
        raw_alpha = self._combine_factors(factors)

        # market-neutral
        neutral = raw_alpha - raw_alpha.mean()

        final = self._post_process(neutral)
        return final.fillna(0.0)
