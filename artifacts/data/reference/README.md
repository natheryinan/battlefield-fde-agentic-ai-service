# reference – 参考表 / 常量层 (Reference Layer)

Purpose:
- 存放 **缓慢变化、结构稳定的 lookup / 映射 / 规则表**：
  - 标的主表 / 交易所元数据
  - 行业或分类映射
  - 策略 / Router / Legal / Regime 规则参数（数据化版本）
  - 风险区间阈值表

Characteristics:
- 文件应当：
  - 小、稳定、可直接 join
  - 不受回测区间影响
  - 作为“系统语义的一部分”

Examples:
- `instruments_master.csv`
- `sector_mapping.yaml`
- `risk_bands_config.yaml`

Usage:
- 供 engine / features / reporting 引用
- 不存放时间序列或衍生计算数据
