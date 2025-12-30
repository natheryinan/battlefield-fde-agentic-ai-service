from engine.data.ticker_aliases import resolve_symbol
import pandas as pd
from pathlib import Path

from dataclasses import dataclass
from typing import Optional


def load_price_series(
    symbol: str,
    root_path: str,
    data_dir: str | None = None,
    file_ext: str = "parquet",
):
    """
    Flexible price loader with two path variables:

        root_path / (data_dir?) / (resolved_symbol + "." + file_ext)

    Examples:
        data_dir="index"      -> artifacts/data/index/SPX.parquet
        file_ext="csv"        -> artifacts/data/SPY.csv
    """

    vendor_symbol = resolve_symbol(symbol)

    base = Path(root_path)
    if data_dir:
        base = base / data_dir

    filename = f"{vendor_symbol}.{file_ext}"
    path = base / filename

    df = pd.read_parquet(path) if file_ext == "parquet" else pd.read_csv(path)
    return df


@dataclass
class LoadedAsset:
    """
    Engineering-grade return structure for platform data loading.

    Future-safe design:
    - Fields can be added without breaking callers
    - Keeps semantic clarity between internal symbol & vendor ticker
    """
    symbol: str                 # internal symbol (e.g., INDEX_500)
    vendor_symbol: str          # resolved vendor ticker (e.g., SPX)
    data: pd.DataFrame          # price dataframe
    asset_class: Optional[str] = None
    source: Optional[str] = None
    meta: Optional[dict] = None
