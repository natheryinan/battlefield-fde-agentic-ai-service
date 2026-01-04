

# engine/fde.py

from typing import Any, Dict

from engine.normalizer import (
    to_market_snapshot,
    to_feature_snapshot,
    build_market_like_types,
)
from architecture.data_contracts import FeatureSnapshot
from pipeline.features_builder import FeaturesBuilder


class FDEEngine:
    """
    核心引擎入口：
    - 接受任何乱七八糟的行情输入
    - 通过 normalizer 纠偏成 MarketSnapshot
    - 附带 LIKE TYPES + 变幻方程说明
    - 走 FeaturesBuilder 输出 FeatureSnapshot
    """

    def __init__(self, feature_config: Dict[str, Any]):
        self.features_builder = FeaturesBuilder(feature_config)

    def ingest_market(
        self,
        timestamp: float,
        symbols: Any,
        prices: Any,
        extra: Any = None,
    ) -> FeatureSnapshot:
        """
        外界随便丢什么形状的行情进来：
        - to_market_snapshot: 永恒补得 + 纠偏
        - build_market_like_types: 生成 LIKE TYPES 描述
        - transform_specs: 描述特征的“变幻方程”
        """

        # 1) 先纠偏成永恒 MarketSnapshot
        market = to_market_snapshot(timestamp, symbols, prices, extra)

        # 2) 构造 LIKE TYPES（类型形状 + 示例值）
        like_types = build_market_like_types(market)

        # 3) 构造“变幻方程”说明：
        #    这里先把 FeaturesBuilder 里的两个基本特征写成显式方程说明，
        #    后面你可以扩展 / 替换成从 config 里动态读取。
        transform_specs = {
            "ret_1": {
                "like": "float",
                "equation": "P_t / P_{t-1} - 1",
                "inputs": ["prices"],
                "notes": "基于最后两个价格的简单收益率",
            },
            "vol_window": {
                "like": "float",
                "equation": "std(P_{t-w+1:t})",
                "inputs": ["prices"],
                "params": {
                    "window": self.features_builder.cfg.get("vol_window", 20),
                },
                "notes": "指定窗口内价格标准差",
            },
        }

        # 4) 把值 + LIKE TYPES + 变幻方程打包进 raw_payload
        raw_payload = {
            "timestamp": market.timestamp,
            "symbols": market.symbols,
            "prices": market.prices,
            "extra": market.extra,

            # === 类型值 / LIKE TYPES ===
            "_like_types": like_types,

            # === 变幻方程 ===
            "_transform_specs": transform_specs,
        }

        # 5) 为了兼容现有 FeaturesBuilder.build(raw_batch)，
        #    这里临时构造一个轻量级对象，带有 payload / timestamp 属性。
        RawBatchShim = type("RawBatchShim", (), {})
        rb = RawBatchShim()
        rb.payload = raw_payload
        rb.timestamp = market.timestamp

        features_dict = self.features_builder.build(rb)

        # 6) 再把输出特征也走一遍永恒补得 -> FeatureSnapshot
        return to_feature_snapshot(
            timestamp=features_dict["timestamp"],
            symbols=features_dict["symbols"],
            features=features_dict["features"],
            extra=features_dict.get("extra"),
            like_types=raw_payload.get("_like_types"),
            transform_specs=raw_payload.get("_transform_specs"),
        )
