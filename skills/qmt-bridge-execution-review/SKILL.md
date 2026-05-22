---
name: qmt-bridge-execution-review
description: >-
  通过 QMT Bridge 生成当日交易复盘：委托、成交、滑点、按标的汇总，
  并结合当日盈亏输出操作评价（对照**交易观**：量能分区、板块聚焦、分步止盈/低吸不追涨、戒律检查）。
  在用户提到今日成交、交易复盘、今日操作评估、执行质量、交易观时使用。只读。
---

# QMT Bridge 交易复盘 Skill

> **实现状态**：✅ `daily_trade_report.py` 可用（见 [ROADMAP.md](../ROADMAP.md)）

## 目标

闭合「计划—执行—复盘」中的**复盘**环节：

1. 汇总当日委托与成交，评估滑点与撤单
2. 按标的汇总买卖量
3. **当日操作评价**：结合盈亏拆解与 [交易观标准](references/trading-philosophy.md)，归纳止盈/加仓/逆势、量能与戒律检查

## 脚本

| 脚本 | 作用 |
|------|------|
| `scripts/daily_trade_report.py` | orders + trades + 操作评价；`--json`；`--feishu-md` 飞书全文 |

```bash
python skills/qmt-bridge-execution-review/scripts/daily_trade_report.py --host 127.0.0.1 --port 8080 --api-key KEY
python skills/qmt-bridge-execution-review/scripts/daily_trade_report.py --json --api-key KEY
python skills/qmt-bridge-execution-review/scripts/daily_trade_report.py --host 127.0.0.1 --port 8080 --api-key KEY --feishu-md
```

| 参数 | 说明 |
|------|------|
| `--json` | JSON（含 `operation_evaluation`） |
| `--feishu-md [PATH]` | 导出飞书 Markdown 全文（默认 `reports/feishu_daily_eval.md`） |
| `--no-trades` | 跳过成交列表 |
| `--no-summary` | 跳过按标的汇总 |
| `--no-eval` | 不输出操作评价 |
| `--market-turnover-yi` | 两市成交额（亿元），量能分区评价 |
| `--no-philosophy-fetch` | 不拉指数/近3日涨幅（仅用当日 tick） |

## 提示词示例（可复制）

| 场景 | 提示词 |
|------|--------|
| **复盘+评价（推荐）** | `生成今日交易复盘并做当日操作评价` |
| | `今日操作评估：得失、执行质量、明日纪律` |
| 执行质量 | `汇总今天委托和成交，看看滑点和撤单` |
| 对照盈亏 | `结合当日盈亏评价今天买卖是否合理` |

## 主要 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/trading/orders` | 当日委托 |
| GET | `/api/trading/trades` | 当日成交 |
| GET | `/api/trading/positions` | 持仓（评价用） |
| GET | `/api/trading/asset` | 资金（评价用） |
| GET | `/api/market/full_tick` | 现价/昨收（盈亏估算） |

## 操作规程

1. `health` + `account_status` 确认服务与交易通道
2. 拉 `orders`、`trades`、`positions`、`asset`
3. 输出委托表、成交列表、按标的汇总
4. 计算当日盈亏拆解，生成 **【当日操作评价】**（`--no-eval` 可关）
5. **只输出报告，不下单**

## 操作评价说明

评价依据见 **[references/trading-philosophy.md](references/trading-philosophy.md)**，实现见 `_shared/trading_philosophy.py` + `execution_review_eval.py`。

- **分标的**：操作类型（大涨止盈/逆势加仓/顺势加仓等）、当日盈亏、仓位变化
- **交易观对照**：四板块分布、量能分区、符合顺势/止盈的亮点
- **戒律检查**：追涨、谨慎区重仓买、近3日/单日大涨未止盈、滑点与持仓过散等
- **总评**：1～10 分（含交易观加减分）+ 做得好的 / 需改进 / 执行质量 / 纪律提示
- 统计归纳，**非投资建议**

### 量能参数

复盘脚本支持传入当日两市成交额（亿元）：

```bash
python skills/qmt-bridge-execution-review/scripts/daily_trade_report.py \
  --host 127.0.0.1 --port 8080 --api-key KEY --market-turnover-yi 12500
```

未传入时提示人工对照万亿阈值；指数均涨跌幅与近 3 日累计涨幅默认自动拉取（可用 `--no-philosophy-fetch` 关闭）。

## 安全

- 只读；需 `X-API-Key` 的交易查询端点

## 发布到飞书云文档

同步飞书：**必须先** `--feishu-md` 生成 `reports/feishu_daily_eval.md`，再用 **[qmt-bridge-feishu-doc](../qmt-bridge-feishu-doc/SKILL.md)** + **lark-doc** / **lark-drive** 上传（禁止 Agent 手写正文）。工作流见 `qmt-bridge-feishu-doc/references/workflows/daily-eval-sync.md`。
