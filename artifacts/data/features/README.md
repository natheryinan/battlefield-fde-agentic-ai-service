# features – 特征 / 信号层 (Feature Layer)

Purpose:
- 存放由 `raw/` 派生出的 **特征矩阵 / 信号表**：
  - 技术指标 (vol, returns, momentum, carry, spreads…)
  - 风险特征 (drawdown, skew, kurtosis)
  - alpha input features / factor exposures
  - Routing / Liquidity / Regime 相关信号

Rules:
- 任何文件 **都必须能追溯来源 raw 文件**（via metadata）。
- 命名建议：
  - `features_core_daily_2024-01-01-2025-01-01.parquet`
  - `signals_liquidity_intraday_2025-01.parquet`
- 列字段示例：
  - `timestamp`, `symbol`
  - `feature_*` 或 `signal_*` 统一前缀
- 不在这里存模型输出（PnL 曲线、权重等），那是 `backtests/` 的职责。

Metadata:
- 每个重要特征文件旁边可有一个同名 `.meta.yaml`
  - 记录生成脚本路径
  - raw 来源文件列表
  - 版本号 / git commit hash
