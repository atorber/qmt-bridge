---
name: qmt-bridge-daily-pnl
description: >-
  通过 QMT Bridge 查看当日盈亏：结合当前持仓、昨仓与当日买卖成交计算，含已清仓标的。
  在用户提到今日盈亏、当日收益、赚了多少、盘面盈亏时使用。只读。
---

# QMT Bridge 当日盈亏 Skill

> **实现状态**：✅ `daily_pnl_snapshot.py` 可用（见 [ROADMAP.md](../ROADMAP.md)）

## 目标

快速回答「今天账户盈亏多少」：优先 QMT `today_profit_loss`；否则用**持仓 + 当日成交 + 行情**计算（非仅当前持仓量 × 涨跌幅）。

**估算公式**（单标的）：

`当日盈亏 = 现市值 − 昨收×昨仓 − 今日买入金额 + 今日卖出金额`

拆解：昨仓浮动、今买浮动、今卖已实现；**已清仓**但当日有卖出的标的单独列出。

## 脚本

| 脚本 | 作用 |
|------|------|
| `scripts/daily_pnl_snapshot.py` | asset + positions + **trades**，汇总当日盈亏（含已清仓） |

```bash
just agent-daily-pnl --port 8080 --api-key KEY
python skills/qmt-bridge-daily-pnl/scripts/daily_pnl_snapshot.py --json
```

## 主要 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/trading/positions` | 持仓（含昨仓、QMT 当日盈亏等） |
| GET | `/api/trading/trades` | **当日成交**（买卖金额） |
| GET | `/api/trading/asset` | 资产 |
| GET | `/api/market/full_tick` | 现价/昨收 |
| GET | `/api/utility/batch_stock_name` | 中文名称 |

## 操作规程

1. 拉 `positions`、`trades`、`asset`
2. 按标的汇总当日买入/卖出量与金额；昨仓优先 `yesterday_volume`，否则 `现仓 − 今买 + 今卖`
3. 有 QMT `today_profit_loss` 则直接采用；否则用上述公式 + `full_tick` 现价/昨收
4. 输出持仓标的与**当日已清仓**标的；可选 `--no-detail` 隐藏拆解
5. **只读**；与柜台可能有手续费/分红等细微差异

## 安全

- 只读；交易查询需 `X-API-Key`
- 不提供投资建议式结论

## 参考

- [qmt-bridge-portfolio-risk](../qmt-bridge-portfolio-risk/SKILL.md) · [qmt-bridge-execution-review](../qmt-bridge-execution-review/SKILL.md)
- `docs/rest-api.md`
