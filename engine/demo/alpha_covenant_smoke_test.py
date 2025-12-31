from __future__ import annotations

from datetime import datetime, timedelta
from pprint import pprint

from engine.personas.alpha_law import AlphaLawConfig, AlphaLawClock
from engine.bootstrap.alpha_wrapped_fde import AlphaWrappedFDE


def build_alpha_covenant_clock() -> AlphaLawClock:
    """
    Create a simple Alpha covenant clock:
      - 10-minute slots
      - 1 blade allowed per slot
    """
    config = AlphaLawConfig(
        covenant_id="COVENANT-FDE-CORE-001",
        slot_duration=timedelta(minutes=10),
        allow_blade=True,
        max_blades_per_slot=1,
    )
    clock = AlphaLawClock.from_config(config)
    return clock


def run_scenario():
    clock = build_alpha_covenant_clock()
    fde = AlphaWrappedFDE(alpha_law_clock=clock)

    # --- personas & scales ---
    persona_scales = {
        "alpha": 1.0,
        "guardian": 0.7,
        "omega": 0.5,
        "convexity": 0.4,
    }

    # no legal overrides for now
    legal_overrides = {}

    start = datetime.utcnow()

    print("\n=== SLOT 0 — NORMAL-ish LIQUID MARKET ===")
    routed_0 = fde.step(
        price=100.0,
        volatility=0.01,           # very small; under baseline
        volume=1_000_000.0,
        volume_pressure=1.0,
        drawdown=0.02,
        liquidity_score=0.9,       # deep liquidity
        extra_obs={"tag": "normal_liquid"},
        persona_decisions={
            "alpha": {"target_notional": 1.0, "target_leverage": 2.0},
            "guardian": {"target_notional": 0.5},
            "omega": {"target_notional": 0.7},
            "convexity": {"target_notional": 0.3},
        },
        persona_scales=persona_scales,
        legal_overrides=legal_overrides,
        timestamp=start,
    )
    pprint({k: (v.approved_notional, v.approved_leverage, v.rejected) for k, v in routed_0.items()})

    # --- Alpha uses blade mid-slot: seals everyone else for the rest of slot 0 ---
    print("\n>>> ALPHA USES BLADE IN SLOT 0")
    blade_event = clock.register_blade(reason="crash_containment_test", when=start + timedelta(minutes=3))
    print("Blade event:", blade_event)

    print("\n=== SLOT 0 — AFTER BLADE (OTHERS SHOULD BE ZEROED) ===")
    routed_0b = fde.step(
        price=95.0,
        volatility=0.03,           # slightly elevated
        volume=1_200_000.0,
        volume_pressure=1.4,
        drawdown=0.05,
        liquidity_score=0.85,
        extra_obs={"tag": "post_blade_same_slot"},
        persona_decisions={
            "alpha": {"target_notional": 1.2, "target_leverage": 2.5},
            "guardian": {"target_notional": 0.6},
            "omega": {"target_notional": 0.8},
            "convexity": {"target_notional": 0.4},
        },
        persona_scales=persona_scales,
        legal_overrides=legal_overrides,
        timestamp=start + timedelta(minutes=4),
    )
    pprint({k: (v.approved_notional, v.approved_leverage, v.rejected) for k, v in routed_0b.items()})

    # --- Advance to next slot: covenant continues, slot resets state ---
    print("\n>>> ADVANCE TO SLOT 1")
    clock.advance_to_next_slot(start_time=start + timedelta(minutes=10))

    print("\n=== SLOT 1 — LIQUIDITY THINS → CRASH ===")
    routed_1 = fde.step(
        price=80.0,
        volatility=0.20,           # big volatility shock
        volume=2_000_000.0,
        volume_pressure=4.0,       # above threshold
        drawdown=-0.35,             # > crash_drawdown
        liquidity_score=0.05,      # BELOW liquidity_freeze_level → frozen
        extra_obs={"tag": "illiquidity_crash"},
        persona_decisions={
            "alpha": {"target_notional": 1.5, "target_leverage": 3.0},
            "guardian": {"target_notional": 0.4},
            "omega": {"target_notional": 0.9},
            "convexity": {"target_notional": 0.5},
        },
        persona_scales=persona_scales,
        legal_overrides=legal_overrides,
        timestamp=start + timedelta(minutes=11),
    )
    pprint({
        k: {
            "approved_notional": v.approved_notional,
            "approved_leverage": v.approved_leverage,
            "rejected": v.rejected,
            "regime": v.regime_state.name,
            "reasons": v.regime_state.guardian_reasons,
        }
        for k, v in routed_1.items()
    })


if __name__ == "__main__":
    run_scenario()
