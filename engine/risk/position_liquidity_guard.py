from mpl_toolkits.mplot3d import Axes3D  # noqa: F401  # needed for 3D projection

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

from engine.risk.position_liquidity_guard import PositionLiquidityGuard


FIG_DIR = Path("artifacts/figures/position_liquidity_guard")


def _ensure_fig_dir():
    FIG_DIR.mkdir(parents=True, exist_ok=True)


def _save_and_close(fig, name: str):
    _ensure_fig_dir()
    out_path = FIG_DIR / f"{name}.png"
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)
    print(f"[AUTOGRAPHY] Saved: {out_path}")


def plot_shock_throttle_curve(guard: PositionLiquidityGuard):
    vols = np.linspace(0.002, 0.20, 375)
    throttles = [guard._shock_throttle(v) for v in vols]

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.set_title("Shock Throttle vs Volatility")
    ax.set_xlabel("Volatility")
    ax.set_ylabel("shock_throttle(vol)")
    ax.plot(vols, throttles)
    ax.grid(True, linestyle=":")

    _save_and_close(fig, "01_shock_throttle_vs_volatility")


def plot_effective_leverage_curve(guard: PositionLiquidityGuard):
    vols = np.linspace(0.002, 0.20, 375)
    levs = [guard._effective_leverage(v) for v in vols]

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.set_title("Effective Leverage vs Volatility")
    ax.set_xlabel("Volatility")
    ax.set_ylabel("effective_leverage(vol)")
    ax.plot(vols, levs)
    ax.grid(True, linestyle=":")

    _save_and_close(fig, "02_effective_leverage_vs_volatility")


def plot_position_slices(guard: PositionLiquidityGuard, raw_signal: float = 1.0):
    vols = np.linspace(0.002, 0.20, 375)
    liquidity_levels = [0.25, 0.5, 0.75, 1.0]

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.set_title(f"Position vs Volatility (raw_signal={raw_signal})")
    ax.set_xlabel("Volatility")
    ax.set_ylabel("Position size")

    for liq in liquidity_levels:
        positions = [
            guard.compute_position(raw_signal, v, liq) for v in vols
        ]
        ax.plot(vols, positions, label=f"liquidity={liq:.2f}")

    ax.grid(True, linestyle=":")
    ax.legend()

    _save_and_close(fig, "03_position_vs_volatility_slices")


# ============= HEATMAPS: THROTTLE / LEVERAGE / POSITIONS =============

def plot_throttle_heatmap(guard: PositionLiquidityGuard):
    """
    Heatmap of shock_throttle(volatility) over (volatility, liquidity).
    Throttle does not depend on liquidity, so bands will be horizontal.
    """
    vol_grid = np.linspace(0.002, 0.20, 276)
    liq_grid = np.linspace(0.1, 1.0, 160)

    V, L = np.meshgrid(vol_grid, liq_grid)
    T = np.zeros_like(V)

    for i in range(L.shape[0]):
        for j in range(V.shape[1]):
            T[i, j] = guard._shock_throttle(V[i, j])

    fig, ax = plt.subplots(figsize=(7, 5))
    im = ax.imshow(
        T,
        origin="lower",
        extent=[vol_grid.min(), vol_grid.max(), liq_grid.min(), liq_grid.max()],
        aspect="auto",
    )
    ax.set_title("Heatmap – Shock Throttle (volatility vs liquidity)")
    ax.set_xlabel("Volatility")
    ax.set_ylabel("Liquidity score")
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("shock_throttle(vol)")

    _save_and_close(fig, "04_throttle_heatmap_vol_vs_liquidity")


def plot_leverage_heatmap(guard: PositionLiquidityGuard):
    """
    Heatmap of effective_leverage(volatility) over (volatility, liquidity).
    Leverage depends only on vol; liquidity dimension is a visual band.
    """
    vol_grid = np.linspace(0.002, 0.20, 276)
    liq_grid = np.linspace(0.1, 1.0, 160)

    V, L = np.meshgrid(vol_grid, liq_grid)
    E = np.zeros_like(V)

    for i in range(L.shape[0]):
        for j in range(V.shape[1]):
            E[i, j] = guard._effective_leverage(V[i, j])

    fig, ax = plt.subplots(figsize=(7, 5))
    im = ax.imshow(
        E,
        origin="lower",
        extent=[vol_grid.min(), vol_grid.max(), liq_grid.min(), liq_grid.max()],
        aspect="auto",
    )
    ax.set_title("Heatmap – Effective Leverage (volatility vs liquidity)")
    ax.set_xlabel("Volatility")
    ax.set_ylabel("Liquidity score")
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("effective_leverage(vol)")

    _save_and_close(fig, "05_leverage_heatmap_vol_vs_liquidity")


def plot_position_heatmap(guard: PositionLiquidityGuard, raw_signal: float = 1.0):
    """
    Heatmap of resulting position over volatility x liquidity.
    This is the combined effect of throttle + leverage + liquidity weighting.
    """
    vol_grid = np.linspace(0.002, 0.20, 160)
    liq_grid = np.linspace(0.1, 1.0, 160)

    V, L = np.meshgrid(vol_grid, liq_grid)
    P = np.zeros_like(V)

    for i in range(L.shape[0]):
        for j in range(V.shape[1]):
            P[i, j] = guard.compute_position(raw_signal, V[i, j], L[i, j])

    fig, ax = plt.subplots(figsize=(7, 5))
    im = ax.imshow(
        P,
        origin="lower",
        extent=[vol_grid.min(), vol_grid.max(), liq_grid.min(), liq_grid.max()],
        aspect="auto",
    )
    ax.set_title(f"Heatmap – Position (raw_signal={raw_signal})")
    ax.set_xlabel("Volatility")
    ax.set_ylabel("Liquidity score")
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Position size")

    _save_and_close(fig, "06_position_heatmap_vol_vs_liquidity")


# ================== 3D SURFACE / SPECTRUM VIEWS ==================

def plot_throttle_surface_3d(guard: PositionLiquidityGuard):
    """
    3D surface: shock_throttle(vol) over (volatility, liquidity).
    Liquidity is a dummy axis here but gives full 3D geometry.
    """
    vol_grid = np.linspace(0.002, 0.20, 80)
    liq_grid = np.linspace(0.1, 1.0, 80)

    V, L = np.meshgrid(vol_grid, liq_grid)
    Z = np.zeros_like(V)

    for i in range(L.shape[0]):
        for j in range(V.shape[1]):
            Z[i, j] = guard._shock_throttle(V[i, j])

    fig = plt.figure(figsize=(8, 6))
    ax = fig.add_subplot(111, projection="3d")
    ax.view_init(elev=30, azim=235)

    surf = ax.plot_surface(V, L, Z, linewidth=0, antialiased=True)

    ax.set_title("3D Spectrum – Shock Throttle")
    ax.set_xlabel("Volatility")
    ax.set_ylabel("Liquidity score")
    ax.set_zlabel("shock_throttle(vol)")

    fig.colorbar(surf, shrink=0.5, aspect=10, ax=ax)

    _save_and_close(fig, "07_throttle_surface_3d")


def plot_leverage_surface_3d(guard: PositionLiquidityGuard):
    """
    3D surface: effective_leverage(vol) over (volatility, liquidity).
    """
    vol_grid = np.linspace(0.002, 0.20, 80)
    liq_grid = np.linspace(0.1, 1.0, 80)

    V, L = np.meshgrid(vol_grid, liq_grid)
    Z = np.zeros_like(V)

    for i in range(L.shape[0]):
        for j in range(V.shape[1]):
            Z[i, j] = guard._effective_leverage(V[i, j])

    fig = plt.figure(figsize=(8, 6))
    ax = fig.add_subplot(111, projection="3d")
    ax.view_init(elev=30, azim=235)

    surf = ax.plot_surface(V, L, Z, linewidth=0, antialiased=True)

    ax.set_title("3D Spectrum – Effective Leverage")
    ax.set_xlabel("Volatility")
    ax.set_ylabel("Liquidity score")
    ax.set_zlabel("effective_leverage(vol)")

    fig.colorbar(surf, shrink=0.5, aspect=10, ax=ax)

    _save_and_close(fig, "08_leverage_surface_3d")


def plot_position_surface_3d(guard: PositionLiquidityGuard, raw_signal: float = 1.0):
    """
    3D surface: resulting position over (volatility, liquidity).
    This is the true combined spectrum: throttle + leverage + liquidity.
    """
    vol_grid = np.linspace(0.002, 0.20, 80)
    liq_grid = np.linspace(0.1, 1.0, 80)

    V, L = np.meshgrid(vol_grid, liq_grid)
    Z = np.zeros_like(V)

    for i in range(L.shape[0]):
        for j in range(V.shape[1]):
            Z[i, j] = guard.compute_position(raw_signal, V[i, j], L[i, j])

    fig = plt.figure(figsize=(8, 6))
    ax = fig.add_subplot(111, projection="3d")
    ax.view_init(elev=30, azim=235)

    surf = ax.plot_surface(V, L, Z, linewidth=0, antialiased=True)

    ax.set_title(f"3D Spectrum – Position (raw_signal={raw_signal})")
    ax.set_xlabel("Volatility")
    ax.set_ylabel("Liquidity score")
    ax.set_zlabel("Position size")

    fig.colorbar(surf, shrink=0.5, aspect=10, ax=ax)

    _save_and_close(fig, "09_position_surface_3d")


# ===================== NUMERIC STORY =====================

def print_numeric_autography(guard: PositionLiquidityGuard, raw_signal: float = 1.0):
    """
    Small textual autograph: key regimes as numeric checkpoints.
    """
    regimes = [
        ("ultra_calm", 0.005, 1.0),
        ("normal", guard.volatility_baseline, 0.8),
        ("stressed", 0.05, 0.6),
        ("crisis", 0.10, 0.5),
        ("insane", 0.20, 0.3),
    ]

    print("\n[AUTOGRAPHY] PositionLiquidityGuard key checkpoints")
    print("name      vol      liq   throttle   eff_lev   position")
    print("-" * 60)
    for name, vol, liq in regimes:
        throttle = guard._shock_throttle(vol)
        lev = guard._effective_leverage(vol)
        pos = guard.compute_position(raw_signal, vol, liq)
        print(
            f"{name:9s} "
            f"{vol:6.3f}  "
            f"{liq:4.2f}   "
            f"{throttle:8.3f}  "
            f"{lev:7.3f}  "
            f"{pos:8.3f}"
        )
    print("-" * 60)
    print("[AUTOGRAPHY] End of numeric summary\n")


# ===================== FULL RUNNER =====================

def run_full_autography():
    """
    Runs the full picture/autobiography of the guard:
    - Throttle curve
    - Leverage curve
    - Position slices
    - Throttle heatmap (vol x liquidity)
    - Leverage heatmap (vol x liquidity)
    - Position heatmap (vol x liquidity)
    - 3D surfaces for throttle, leverage, position
    - Numeric checkpoints
    """
    guard = PositionLiquidityGuard(
        max_gross_exposure=1.0,
        target_risk=0.02,
        volatility_baseline=0.02,
        max_leverage=2.0,
        liquidity_floor=0.25,
        min_position_fraction=0.05,
    )

    print("[AUTOGRAPHY] Starting PositionLiquidityGuard autography...")
    plot_shock_throttle_curve(guard)
    plot_effective_leverage_curve(guard)
    plot_position_slices(guard, raw_signal=1.0)

    # 2D heatmaps
    plot_throttle_heatmap(guard)
    plot_leverage_heatmap(guard)
    plot_position_heatmap(guard, raw_signal=1.0)

    # 3D spectra
    plot_throttle_surface_3d(guard)
    plot_leverage_surface_3d(guard)
    plot_position_surface_3d(guard, raw_signal=1.0)

    print_numeric_autography(guard)
    print("[AUTOGRAPHY] All figures generated.")


if __name__ == "__main__":
    run_full_autography()
