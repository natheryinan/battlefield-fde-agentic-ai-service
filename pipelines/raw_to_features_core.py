"""
pipelines/raw_to_features_core.py

Purpose:
    从 artifacts/data/raw 读取基础行情数据，
    生成 FDE Core 所需的“核心特征矩阵”到 artifacts/data/features。

Notes:
    - 这是一个可运行的 pipeline 骨架。
    - 实际特征工程（如何算因子/信号）和更新逻辑，
      可以在 build_core_features() 和 apply_update_mode() 里逐步扩展。

Update Modes:
    - full  : 全量重建（覆盖旧文件）
    - append: 只对新日期 / 新数据行进行特征计算，然后与旧特征合并去重
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any

import pandas as pd


# 根目录假设为当前脚本上级的上级（你可按需修改）
REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = REPO_ROOT / "artifacts" / "data"
RAW_ROOT = DATA_ROOT / "raw"
FEATURES_ROOT = DATA_ROOT / "features"
REFERENCE_ROOT = DATA_ROOT / "reference"


# ==== 简单配置（以后可以搬去 YAML / reference 层） ====
DEFAULT_FEATURE_CONFIG: Dict[str, Any] = {
    "ret_window": 1,         # 收益窗口
    "vol_window": 20,        # 波动率窗口
    "update_mode": "full",   # "full" or "append"
}


def load_raw_ohlcv(
    filename: str = "market_ohlcv_1d_2024.parquet",
) -> pd.DataFrame:
    """
    从 raw 目录加载 OHLCV 数据。
    """
    path = RAW_ROOT / filename
    if not path.exists():
        raise FileNotFoundError(f"Raw OHLCV file not found: {path}")

    df = pd.read_parquet(path)
    # 标准化基本列名（按你实际数据调整）
    df = df.rename(
        columns={
            "date": "timestamp",
            "ts": "timestamp",
        }
    )
    return df


def build_core_features(
    df: pd.DataFrame,
    feature_config: Optional[Dict[str, Any]] = None,
) -> pd.DataFrame:
    """
    将原始 OHLCV 转换为【核心特征矩阵】。

    当前实现（可运行 demo）：
        - feature_ret_1d   : 简单 1 日收益
        - feature_vol_Nd   : N 日 rolling 波动率

    TODO（你以后可以在这里扩展）：
        - 更多 return horizon (ret_5d, ret_20d, ...)，由 feature_config 控制
        - 更复杂的 risk / microstructure 特征（spread, depth, imbalance ...）
        - 直接输出供 Alpha / Router / Protection 使用的信号列
    """
    cfg = {**DEFAULT_FEATURE_CONFIG, **(feature_config or {})}
    ret_window = int(cfg.get("ret_window", 1))
    vol_window = int(cfg.get("vol_window", 20))

    df = df.copy()

    if not {"timestamp", "symbol", "close"}.issubset(df.columns):
        raise ValueError("Expected columns: timestamp, symbol, close")

    df = df.sort_values(["symbol", "timestamp"])

    # 收益：这里示例用 ret_window，默认 1 日
    df["feature_ret_1d"] = (
        df.groupby("symbol")["close"]
        .pct_change(periods=ret_window)
    )

    # 波动：基于 ret_1d 做 vol_window 期 rolling
    df["feature_vol_20d"] = (
        df.groupby("symbol")["feature_ret_1d"]
        .rolling(window=vol_window, min_periods=max(5, vol_window // 4))
        .std()
        .reset_index(level=0, drop=True)
    )

    core_cols = ["timestamp", "symbol"] + [
        c for c in df.columns if c.startswith("feature_")
    ]
    return df[core_cols].dropna(how="all", subset=core_cols[2:])


def apply_update_mode(
    new_features: pd.DataFrame,
    out_path: Path,
    update_mode: str = "full",
) -> Path:
    """
    根据 update_mode 决定如何处理输出：

    - full:
        直接覆盖写入 new_features
    - append:
        如果 out_path 已存在：
            1) 读取旧特征
            2) 合并旧 + 新
            3) 按 [timestamp, symbol] 去重（保留最新）
        否则：
            直接写入 new_features
    """
    update_mode = (update_mode or "full").lower()
    FEATURES_ROOT.mkdir(parents=True, exist_ok=True)

    if update_mode == "full" or not out_path.exists():
        new_features.to_parquet(out_path, index=False)
        return out_path

    # append 模式：合并旧 + 新
    old = pd.read_parquet(out_path)
    combined = pd.concat([old, new_features], axis=0, ignore_index=True)

    # 去重逻辑：以 (timestamp, symbol) 作为 key，保留最后一条
    combined = (
        combined.sort_values(["timestamp", "symbol"])
        .drop_duplicates(subset=["timestamp", "symbol"], keep="last")
    )

    combined.to_parquet(out_path, index=False)
    return out_path


def save_core_features(
    features: pd.DataFrame,
    filename: str = "features_core_daily_2024.parquet",
    update_mode: str = "full",
) -> Path:
    """
    将核心特征矩阵保存到 features 目录，支持 full / append。

    update_mode:
        - "full"   : 重建整个文件
        - "append" : 在已有特征文件基础上增量更新
    """
    out_path = FEATURES_ROOT / filename
    out_path = apply_update_mode(features, out_path, update_mode=update_mode)
    return out_path


def main(
    raw_filename: Optional[str] = None,
    out_filename: Optional[str] = None,
    feature_config: Optional[Dict[str, Any]] = None,
):
    raw_filename = raw_filename or "market_ohlcv_1d_2024.parquet"
    out_filename = out_filename or "features_core_daily_2024.parquet"

    cfg = {**DEFAULT_FEATURE_CONFIG, **(feature_config or {})}
    update_mode = cfg.get("update_mode", "full")

    print(f"[raw_to_features_core] Loading raw from: {raw_filename}")
    df_raw = load_raw_ohlcv(raw_filename)

    print(f"[raw_to_features_core] Building core features (ret={cfg['ret_window']}, vol={cfg['vol_window']})...")
    df_features = build_core_features(df_raw, feature_config=cfg)

    print(f"[raw_to_features_core] Saving features to: {out_filename} (mode={update_mode})")
    out_path = save_core_features(df_features, out_filename, update_mode=update_mode)

    print(f"[raw_to_features_core] Done. Output: {out_path}")


if __name__ == "__main__":
    main()
