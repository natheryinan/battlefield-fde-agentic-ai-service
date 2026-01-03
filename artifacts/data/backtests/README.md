
# backtests – 回测结果层 (Backtest Layer)

Purpose:
- 存放 FDE / Alpha / Router / Liquidity Protection 的
  **回测与模拟输出资产**，包括：
  - 交易明细（fills, orders）
  - 资金曲线 / 账户权益
  - 风险指标时间序列
  - 版本化性能评估记录（可追溯）

Naming Rules:
- 一个回测版本使用统一前缀：
  - `fde_core_v155_equity_curve.parquet`
  - `fde_core_v155_trades.parquet`
  - `fde_core_v155_risk_metrics.csv`
  - `fde_core_v155_summary.yaml`

General Principles:
- 回测必须能追溯：
  - 使用的 experiment yaml
  - 所属 features 版本
  - 时间区间
- 所有结果文件 **只记录输出，不含业务逻辑**

Recommended Artifacts:
- `*_equity_curve.*`
- `*_trades.*`
- `*_risk_metrics.*`
- `*_summary.yaml`
