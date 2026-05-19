# Skills 实现路线图

各 Skill 的 `SKILL.md` 与可执行脚本已对齐；共享模块见 [`_shared/`](_shared/)。

## 实现状态图例

| 标记 | 含义 |
|------|------|
| ✅ | 脚本可用 |
| ⏸ | 按需使用（如无两融账户可跳过 credit） |

## 全部 Skill 状态

| 优先级 | Skill | 状态 | 脚本 |
|--------|-------|------|------|
| P0 | [qmt-bridge-trading](qmt-bridge-trading/SKILL.md) | ✅ | `trading_status.py`, `place_order.py`, `liquidate.py` |
| P0 | [qmt-bridge-execution-review](qmt-bridge-execution-review/SKILL.md) | ✅ | `daily_trade_report.py` |
| P0 | [qmt-bridge-portfolio-risk](qmt-bridge-portfolio-risk/SKILL.md) | ✅ | `portfolio_snapshot.py` |
| P0 | [qmt-bridge-daily-pnl](qmt-bridge-daily-pnl/SKILL.md) | ✅ | `daily_pnl_snapshot.py` |
| P0 | [qmt-bridge-order-ops](qmt-bridge-order-ops/SKILL.md) | ✅ | `list_orders.py`, `cancel_orders.py` |
| P1 | [qmt-bridge-return-analysis](qmt-bridge-return-analysis/SKILL.md) | ✅ | `return_probability_analysis.py` |
| P1 | [qmt-bridge-market-watch](qmt-bridge-market-watch/SKILL.md) | ✅ | `watchlist_snapshot.py` |
| P1 | [qmt-bridge-sector-theme](qmt-bridge-sector-theme/SKILL.md) | ✅ | `sector_rank.py` |
| P1 | [qmt-bridge-financial-download](qmt-bridge-financial-download/SKILL.md) | ✅ | `download_financial_data.py` |
| P1 | [qmt-bridge-fundamental-screen](qmt-bridge-fundamental-screen/SKILL.md) | ✅ | `screen_financial.py` |
| P1 | [qmt-bridge-technical-signal](qmt-bridge-technical-signal/SKILL.md) | ✅ | `formula_check.py` |
| P2 | [qmt-bridge-smart-execution](qmt-bridge-smart-execution/SKILL.md) | ✅ | `execution_preview.py` |
| P2 | [qmt-bridge-rebalance](qmt-bridge-rebalance/SKILL.md) | ✅ | `rebalance_plan.py` |
| P2 | [qmt-bridge-credit-margin](qmt-bridge-credit-margin/SKILL.md) | ✅ | `credit_snapshot.py` |
| P3 | [qmt-bridge-realtime-monitor](qmt-bridge-realtime-monitor/SKILL.md) | ✅ | `ws_subscribe.py` + SKILL 规程 |
| P3 | [qmt-bridge-event-calendar](qmt-bridge-event-calendar/SKILL.md) | ✅ | `calendar_check.py` |
| P4 | [qmt-bridge-etf](qmt-bridge-etf/SKILL.md) | ⏸ | `etf_snapshot.py`（按需） |
| P4 | [qmt-bridge-convertible](qmt-bridge-convertible/SKILL.md) | ⏸ | `cb_snapshot.py`（按需） |
| P4 | [qmt-bridge-option](qmt-bridge-option/SKILL.md) | ⏸ | `option_chain_snapshot.py`（按需） |
| P4 | [qmt-bridge-hk-connect](qmt-bridge-hk-connect/SKILL.md) | ⏸ | `hk_universe.py`（按需） |

## just 快捷命令

```bash
just agent-trading-status
just agent-daily-report
just agent-portfolio-risk
just agent-daily-pnl
just agent-return-analysis --codes 000001.SZ
just agent-list-orders
just agent-watchlist --codes 000001.SZ
just agent-formula-check --list
just agent-execution-preview 000001.SZ --buy --volume 100
```

完整列表见仓库根目录 `justfile` 中 `Agent` 相关段落。

## 设计约束

- 研究类只读；写操作须 `--execute --confirm`
- 输出摘要，避免 dump 全量 JSON
- 不提供投资建议式结论
