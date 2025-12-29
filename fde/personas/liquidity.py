# fde/personas/liquidity.py
from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Dict, Any

from fde.personas.base import BasePersona, PersonaContext
from fde.interfaces.market import MarketSnapshot
from fde.interfaces.risk import PortfolioState


class LiquidityPersona(BasePersona):
    """
    FDE-Liquidity V2:
    Fully automated SP500 index trend prediction + top-10 constituents tracking.

    Steps:
      1. Predict SPX next-step direction using:
         - momentum(1D, 5D)
         - volatility regime
         - breadth (% stocks above MA)
         - risk-off trigger (VIX-like proxy)
      2. Identify S&P500 top-10 names by market cap.
      3. Apply index prediction signal to these 10 names.
      4. Produce continuous signals between -1 and +1.
    """

    name = "FDE-Liquidity"
    description = "Automated SP500 index forecasting + top-10 constituents tracker."

    def __init__(self, config: Dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self.ema_alpha = float(self.config.get("ema_alpha", 0.20))
        self.prev_signal = None

    # -----------------------------------------------
    # Helper: normalize signals to [-1,1]
    # -----------------------------------------------
    @staticmethod
    def _norm(x: float) -> float:
        return float(max(min(x, 1.0), -1.0))

    # -----------------------------------------------
    # Predict SP500 trend (SPX/ SPY)
    # -----------------------------------------------
    def _predict_spx(self, history: pd.DataFrame) -> float:
        """
        Input history: MultiIndex (date, symbol) with fields ['close', 'mcap']
        We compute index-level:
          - 1D return
          - 5D return
          - realized volatility
          - market breadth
          - risk indicator (inverse volatility)
        Output: number between [-1,1]
        """

        close = history['close'].unstack()
        # pick SPY or use average
        if "SPY" in close.columns:
            spx = close["SPY"]
        else:
            spx = close.mean(axis=1)

        ret1 = spx.pct_change().iloc[-1]
        ret5 = (spx.iloc[-1] / spx.iloc[-6] - 1)

        # realized vol (20D)
        vol20 = spx.pct_change().rolling(20).std().iloc[-1]

        # market breadth: % of stocks above 20D MA
        ma20 = close.rolling(20).mean()
        breadth = (close.iloc[-1] > ma20.iloc[-1]).mean()

        # simple risk-on/off indicator (low vol → risk-on)
        risk_indicator = (0.02 - vol20) * 10

        # combine
        score = (
            1.5 * ret1 +
            1.0 * ret5 +
            1.0 * (breadth - 0.5) +
            0.5 * risk_indicator
        )

        return self._norm(score)

    # -----------------------------------------------
    # Identify top-10 S&P500 constituents
    # -----------------------------------------------
    def _top10_symbols(self, history: pd.DataFrame) -> list[str]:
        mcap = history["mcap"].unstack()
        last_row = mcap.iloc[-1].dropna()
        top10 = last_row.sort_values(ascending=False).head(10).index.tolist()
        return top10

    # -----------------------------------------------
    # MAIN SIGNAL: SPX Forecast → Top-10 stocks
    # -----------------------------------------------
    def compute_signals(
        self,
        snapshot: MarketSnapshot,
        portfolio: PortfolioState,
        ctx: PersonaContext,
    ) -> pd.Series:

        # Expect SP500 history passed inside snapshot.features["history"]
        if snapshot.features is None or "history" not in snapshot.features:
            raise RuntimeError("SP500 Liquidity Persona requires `history` data.")

        history = snapshot.features["history"]
        prices = snapshot.prices

        # 1. predict the SPX direction
        spx_signal = self._predict_spx(history)

        # 2. get top-10 stocks
        top10 = self._top10_symbols(history)

        # create empty signals
        signals = pd.Series(0.0, index=prices.index)

        # 3. assign index signal to top-10 names
        for symbol in top10:
            if symbol in signals.index:
                signals[symbol] = spx_signal

        # 4. smooth the signal using EMA
        if self.prev_signal is None:
            smoothed = signals
        else:
            smoothed = (
                self.ema_alpha * signals
                + (1 - self.ema_alpha) * self.prev_signal
            )

        self.prev_signal = smoothed

        # 5. normalize to [-1,1]
        smoothed = smoothed.clip(-1, 1)

        return smoothed.fillna(0.0)
