from pathlib import Path
import pandas as pd
from engine.data.ticker_aliases import resolve_symbol
from engine.data.loader import load_price_series


def load_platform_universe(
    symbols: list[str],
    root_path: str,
    data_dir: str | None = None,
    file_ext: str = "parquet",
):
    """
    Load all symbols in the platform universe.

    Returns:
        dict[str, pd.DataFrame]
        {
          "SPY": <df>,
          "QQQ": <df>,
          "INDEX_500": <df of SPX>,
          ...
        }
    """

    data = {}

    for sym in symbols:
        vendor = resolve_symbol(sym)

        df = load_price_series(
            symbol=sym,
            root_path=root_path,
            data_dir=data_dir,
            file_ext=file_ext,
        )

        data[sym] = df
        print(f"[platform] loaded {sym} -> {vendor} ({len(df)} rows)")

    return data


