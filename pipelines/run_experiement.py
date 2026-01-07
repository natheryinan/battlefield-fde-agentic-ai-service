# pipeline/run_experiment.py

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Dict, Any, Tuple

import yaml  # pip install pyyaml

from architecture.data.schemas import (
    UniverseDefinition,
    RiskLimits,
    DecisionRequest,
    DecisionResponse,
    Instrument,
)
from architecture.model.fde_core_spec import FDECore
from architecture.data.confacts_presets import INDEX_FLEX


# --- Experiment configuration model -----------------------------------------


@dataclass
class ExperimentConfig:
    experiment_id: str
    description: str
    start_date: dt.date
    end_date: dt.date
    mode: str  # "BACKTEST" | ...
    data_source: str
    universe_name: str
    base_risk_limits: RiskLimits
    engine_params: Dict[str, Any]
    eval_params: Dict[str, Any]


def load_experiment_config(path: str | Path) -> ExperimentConfig:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    meta = raw["experiment"]
    risk = raw["risk_limits"]
    engine = raw.get("engine", {})
    eval_params = raw.get("evaluation", {})

    cfg = ExperimentConfig(
        experiment_id=meta["id"],
        description=meta.get("description", ""),
        start_date=dt.date.fromisoformat(meta["start_date"]),
        end_date=dt.date.fromisoformat(meta["end_date"]),
        mode=meta.get("mode", "BACKTEST"),
        data_source=raw["data"]["source"],
        universe_name=raw["data"]["universe_name"],
        base_risk_limits=RiskLimits(
            max_drawdown_pct=risk["max_drawdown_pct"],
            max_leverage=risk["max_leverage"],
            max_gross_exposure_pct=risk["max_gross_exposure_pct"],
            max_single_name_pct=risk["max_single_name_pct"],
            max_turnover_pct_per_day=risk.get("max_turnover_pct_per_day", 100.0),
            extra=risk.get("extra", {}),
        ),
        engine_params=engine.get("params", {}),
        eval_params=eval_params,
    )
    return cfg


# --- Data loading stubs ------------------------------------------------------


def load_universe(config: ExperimentConfig) -> UniverseDefinition:
    """
    Placeholder: in artifacts/data you will define the real mapping.
    For now we return an empty (or toy) universe.
    """
    instruments: List[Instrument] = [
        # Example only; you can delete or extend:
        # Instrument(symbol="^SPX", confacts=INDEX_FLEX),
    ]
    return UniverseDefinition(name=config.universe_name, instruments=instruments)


def iter_step_contexts(
    config: ExperimentConfig,
    universe: UniverseDefinition,
) -> Iterable[Dict[str, Any]]:
    """
    Generic step iterator.

    Each yielded item is a dict with at least:
      - 'timestamp'
      - 'snapshot'  (arbitrary dict)
      - 'portfolio' (arbitrary dict)

    Implementation is intentionally FLEX: upstream data loader defines
    the exact shape of snapshot/portfolio.
    """
    # No-op generator by default; safe import.
    if False:  # pragma: no cover
        yield {
            "timestamp": dt.datetime.now(),
            "snapshot": {},
            "portfolio": {
                "cash": 0.0,
                "positions": {},
                "equity": 0.0,
                "leverage": 0.0,
                "pnl": 0.0,
            },
        }


def initial_portfolio_dict(config: ExperimentConfig) -> Dict[str, Any]:
    """
    Simple flat start: all cash, no positions.
    Dict-based portfolio, not a fixed dataclass.
    """
    initial_cash = float(config.eval_params.get("initial_cash", 1_000_000.0))
    return {
        "cash": initial_cash,
        "positions": {},  # symbol -> any structure you like
        "equity": initial_cash,
        "leverage": 0.0,
        "pnl": 0.0,
        "extra": {},
    }


# --- Core experiment loop ----------------------------------------------------


@dataclass
class StepResult:
    step_index: int
    timestamp: dt.datetime
    snapshot: Dict[str, Any]
    portfolio: Dict[str, Any]
    decision: DecisionResponse


class ExperimentRunner:
    """
    Generic experiment runner that is agnostic to FDE implementation.

    State containers (snapshot / portfolio) travel inside metadata
    on DecisionRequest, so the core schemas stay FLEX.
    """

    def __init__(self, engine: FDECore, config: ExperimentConfig) -> None:
        self.engine = engine
        self.config = config

    def run(self) -> Tuple[List[StepResult], Dict[str, Any]]:
        """
        Execute a full backtest episode.

        Returns:
            step_results: per-step decisions & state
            summary: aggregate metrics (PnL, breaches, etc.)
        """
        universe = self.engine.universe
        portfolio = initial_portfolio_dict(self.config)
        self.engine.reset()

        step_results: List[StepResult] = []
        total_violations: int = 0

        for step_idx, ctx in enumerate(
            iter_step_contexts(self.config, universe)
        ):
            timestamp: dt.datetime = ctx.get("timestamp", dt.datetime.utcnow())
            snapshot: Dict[str, Any] = ctx.get("snapshot", {})
            portfolio = ctx.get("portfolio", portfolio)  # allow loader to update

            request = DecisionRequest(
                universe=universe,
                risk_limits=self.config.base_risk_limits,
                step_index=step_idx,
                mode=self.config.mode,
                metadata={
                    "timestamp": timestamp,
                    "snapshot": snapshot,
                    "portfolio": portfolio,
                    "experiment_id": self.config.experiment_id,
                },
            )

            decision = self.engine.decide(request)
            total_violations += len(decision.violations)

            # Portfolio update hook:
            # Downstream implementation can mutate portfolio based on decision.
            portfolio = self._apply_decision_to_portfolio(
                portfolio=portfolio,
                decision=decision,
                snapshot=snapshot,
                timestamp=timestamp,
            )

            step_results.append(
                StepResult(
                    step_index=step_idx,
                    timestamp=timestamp,
                    snapshot=snapshot,
                    portfolio=portfolio,
                    decision=decision,
                )
            )

        summary = {
            "experiment_id": self.config.experiment_id,
            "n_steps": len(step_results),
            "total_violations_events": total_violations,
        }
        return step_results, summary

    # --- internal helpers ----------------------------------------------------

    def _apply_decision_to_portfolio(
        self,
        portfolio: Dict[str, Any],
        decision: DecisionResponse,
        snapshot: Dict[str, Any],
        timestamp: dt.datetime,
    ) -> Dict[str, Any]:
        """
        Minimal placeholder: returns portfolio unchanged.

        You can replace this with real PnL / fills / slippage logic.
        """
        # example: stamp timestamp so the structure is time-aware
        portfolio = dict(portfolio)
        portfolio["last_timestamp"] = timestamp.isoformat()
        return portfolio
