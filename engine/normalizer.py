# engine/normalizer.py

from typing import Any, Dict, List, Sequence, Mapping

from architecture.data_contracts import MarketSnapshot, FeatureSnapshot


# ===== 内部小工具：纠偏 =====

def _normalize_symbols(symbols: Any) -> List[str]:
    """
    永恒补得：把外界任何奇怪的 symbols 输入，统一变成 List[str]。
    """
    if symbols is None:
        return []

    # 单个字符串 => ["AAPL"]
    if isinstance(symbols, str):
        return [symbols]

    # list / tuple / 其他序列
    if isinstance(symbols, Sequence):
        return [str(s) for s in symbols if s is not None]

    # 其他任何类型 => [str(对象)]
    return [str(symbols)]


def _normalize_prices(prices: Any) -> Dict[str, float]:
    """
    永恒补得：把任何 prices 输入，尽量整理成 Dict[str, float]。
    """
    norm: Dict[str, float] = {}

    if prices is None:
        return norm

    # dict 直接处理
    if isinstance(prices, Mapping):
        for k, v in prices.items():
            try:
                norm[str(k)] = float(v)
            except (TypeError, ValueError):
                continue
        return norm

    # 尝试用 dict(...) 转（例如 [("AAPL", 123), ("MSFT", 456)]）
    try:
        as_dict = dict(prices)  # type: ignore[arg-type]
        for k, v in as_dict.items():
            try:
                norm[str(k)] = float(v)
            except (TypeError, ValueError):
                continue
        return norm
    except Exception:
        # 实在转不了，就放弃，返回空 dict
        return norm


def _normalize_dict(value: Any) -> Dict[str, Any]:
    """
    extra / features / like_types / transform_specs 之类：永远要 dict。
    """
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    # 尝试 dict(...)
    try:
        return dict(value)  # type: ignore[arg-type]
    except Exception:
        return {"value": value}


# ===== 对外：统一入口函数 =====

def to_market_snapshot(
    timestamp: float,
    symbols: Any,
    prices: Any,
    extra: Any = None,
) -> MarketSnapshot:
    """
    FDE 引擎统一入口：把外界任何形态的市场输入，
    转成“永恒补得”的 MarketSnapshot 实例。
    """
    norm_symbols = _normalize_symbols(symbols)
    norm_prices = _normalize_prices(prices)
    norm_extra = _normalize_dict(extra)

    return MarketSnapshot(
        timestamp=timestamp,
        symbols=norm_symbols,
        prices=norm_prices,
        extra=norm_extra,
    )


def to_feature_snapshot(
    timestamp: float,
    symbols: Any,
    features: Any,
    extra: Any = None,
    like_types: Any = None,
    transform_specs: Any = None,
) -> FeatureSnapshot:
    """
    FDE 引擎统一入口：把特征层输入，转成永恒补得 FeatureSnapshot。
    """
    norm_symbols = _normalize_symbols(symbols)
    norm_features = _normalize_dict(features)
    norm_extra = _normalize_dict(extra)
    norm_like_types = _normalize_dict(like_types)
    norm_transform_specs = _normalize_dict(transform_specs)

    return FeatureSnapshot(
        timestamp=timestamp,
        symbols=norm_symbols,
        features=norm_features,
        extra=norm_extra,
        like_types=norm_like_types,
        transform_specs=norm_transform_specs,
    )


# ===== LIKE TYPES 描述构造 =====

def build_market_like_types(market: MarketSnapshot) -> Dict[str, Any]:
    """
    根据当前 MarketSnapshot 构造一份 LIKE TYPES 描述：
    - 不是真正的 type system，而是“类型形状 / value-like 类型”的说明书。
    """
    return {
        "timestamp": {
            "like": "scalar/float",
            "value_example": float(market.timestamp),
        },
        "symbols": {
            "like": "sequence/str",
            "len": len(market.symbols),
            "value_example": market.symbols[:5],
        },
        "prices": {
            "like": "mapping[str->float]",
            "len": len(market.prices),
            "sample_keys": list(market.prices.keys())[:5],
        },
        "extra": {
            "like": "mapping[str->Any]",
            "known_keys": list(market.extra.keys())[:10],
        },
    }
