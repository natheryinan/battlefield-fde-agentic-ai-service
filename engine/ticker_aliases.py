
"""
ticker_aliases.py

Central place for symbol normalization and alias resolution in the FDE Engine.

Design:
- The engine and configs (YAML) are allowed to use *internal symbols*
  like "INDEX_500".
- The data layer (parquet / vendor) may use vendor tickers such as
  "SPX" or "^GSPC".
- This module provides a small, deterministic mapping between the two.

We keep it:
- strict (no magic guessing),
- explicit (all aliases listed here),
- side-effect free (importing this file does not mutate anything).
"""

from __future__ import annotations

from typing import Dict


# ---------------------------------------------------------------------------
# Core alias table
# ---------------------------------------------------------------------------

# NOTE:
# Keys are *internal* symbols used inside the FDE engine / YAML configs.
# Values are the *canonical* tickers used by your data source.
#
# You can safely change the right-hand side (e.g. "SPX" -> "^GSPC")
# without touching any engine code or YAML, as long as the data source
# understands it.
ALIASES: Dict[str, str] = {
    # === Benchmarks / Indexes =================================================
    # Internal 500-index label used in YAML:
    #   data.universe.symbols: ["SPY", "QQQ", "IWM", "INDEX_500"]
    # will be resolved to the real ticker "SPX" when loading data.
    "INDEX_500": "SPX",

    # If later you want a pure "risk-free" internal label:
    # "RF_RATE": "USD_OIS",

    # Add more here as needed:
    # "INDEX_WORLD": "ACWI",
    # "INDEX_EM": "EEM",
}

# Build a reverse table for inspection or sanity checks if needed.
# This is NOT used in the main path, just available.
REVERSE_ALIASES: Dict[str, str] = {v: k for k, v in ALIASES.items()}


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------

def _normalize_symbol(symbol: str) -> str:
    """
    Canonical string form used as key lookup:
    - strip whitespace
    - uppercase

    We do NOT:
    - try to handle vendor-specific quirks
    - guess exchanges / suffixes

    All those are left to the data vendor side.
    """
    return symbol.strip().upper()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def resolve_symbol(symbol: str) -> str:
    """
    Map an internal symbol to the canonical data-vendor ticker.

    Examples:
        resolve_symbol("INDEX_500") -> "SPX"
        resolve_symbol("index_500") -> "SPX"
        resolve_symbol("SPY")       -> "SPY"  (no change)
    """
    norm = _normalize_symbol(symbol)
    return ALIASES.get(norm, norm)


def is_alias(symbol: str) -> bool:
    """
    True if `symbol` is one of the *internal* alias keys, such as "INDEX_500".
    """
    return _normalize_symbol(symbol) in ALIASES


def canonical_equal(symbol_a: str, symbol_b: str) -> bool:
    """
    Check whether two symbols are equal *after* alias resolution.

    Example:
        canonical_equal("INDEX_500", "SPX")   -> True
        canonical_equal("index_500", "spx")   -> True
        canonical_equal("SPY", "SPY")         -> True
        canonical_equal("SPY", "QQQ")         -> False
    """
    return _normalize_symbol(resolve_symbol(symbol_a)) == _normalize_symbol(
        resolve_symbol(symbol_b)
    )


# ---------------------------------------------------------------------------
# Optional: small self-test (you can delete this if you don't like it)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Minimal sanity check when run directly.
    tests = [
        ("INDEX_500", "SPX"),
        ("index_500", "SPX"),
        ("SPX", "SPX"),
    ]
    for raw, expected in tests:
        resolved = resolve_symbol(raw)
        print(f"{raw!r} -> {resolved!r} (expected {expected!r})")

