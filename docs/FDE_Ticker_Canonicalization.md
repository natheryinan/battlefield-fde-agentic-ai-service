# FDE Ticker Canonicalization Protocol

## 核心原则
FDE 不直接理解外部市场世界的命名体系。
所有输入标的，必须在进入系统前被解析为 FDE Canonical Ticker。

## 为什么必须 Canonicalize
- 不同 broker / 数据源 使用不同命名
- 指数、ETF、期货、衍生物存在多对一关系
- Regime 推断必须基于**同一现实对象**

Canonicalization 是 FDE 的第一道主权边界。

## 定义
Canonical Ticker：
- FDE 内部唯一承认的资产身份标识
- 不随数据源变化
- 不随市场叫法变化

## 示例
| 外部输入 | Canonical |
|--------|-----------|
| ^GSPC  | SP500 |
| SPX   | SP500 |
| SPY   | SP500 |
| ES=F  | SP500 |
| NASDAQ | NASDAQ100 |
| QQQ   | NASDAQ100 |

## 强制规则
- 所有 experiments / backtests / live runs
- 必须通过 `ticker_aliases.py`
- 未被解析的 ticker → 直接拒绝执行
