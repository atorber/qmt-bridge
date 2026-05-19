# Agent Skills

QMT Bridge 在 [`skills/`](../skills/) 提供 **19 个 Agent Skills**，均已配套可执行 Python 脚本与 `just` 快捷命令。

**路线图**：[skills/ROADMAP.md](../skills/ROADMAP.md) · **总览**：[skills/README.md](../skills/README.md)

## 快速开始

```bash
pip install -e .
# 端口以 .env 为准，示例使用 8080
just agent-trading-status --port 8080 --api-key YOUR_KEY
just agent-daily-report --port 8080 --api-key YOUR_KEY
just agent-watchlist --port 8080 --codes 300394.SZ,688008.SH
```

无 `just` 时：

```bash
python skills/qmt-bridge-trading/scripts/trading_status.py --port 8080 --api-key YOUR_KEY
```

Windows 终端中文乱码可执行：`chcp 65001` 或设置 `PYTHONIOENCODING=utf-8`。

## 分类索引

### 交易与执行 ✅

| Skill | 脚本 |
|-------|------|
| [trading](../skills/qmt-bridge-trading/SKILL.md) | `trading_status`, `place_order`, `liquidate` |
| [order-ops](../skills/qmt-bridge-order-ops/SKILL.md) | `list_orders`, `cancel_orders` |
| [smart-execution](../skills/qmt-bridge-smart-execution/SKILL.md) | `execution_preview` |
| [rebalance](../skills/qmt-bridge-rebalance/SKILL.md) | `rebalance_plan` |

### 风控与复盘 ✅

| Skill | 脚本 |
|-------|------|
| [portfolio-risk](../skills/qmt-bridge-portfolio-risk/SKILL.md) | `portfolio_snapshot` |
| [daily-pnl](../skills/qmt-bridge-daily-pnl/SKILL.md) | `daily_pnl_snapshot` |
| [execution-review](../skills/qmt-bridge-execution-review/SKILL.md) | `daily_trade_report` |

### 研究 ✅

| Skill | 脚本 |
|-------|------|
| [market-watch](../skills/qmt-bridge-market-watch/SKILL.md) | `watchlist_snapshot` |
| [sector-theme](../skills/qmt-bridge-sector-theme/SKILL.md) | `sector_rank` |
| [financial-download](../skills/qmt-bridge-financial-download/SKILL.md) | `download_financial_data` |
| [fundamental-screen](../skills/qmt-bridge-fundamental-screen/SKILL.md) | `screen_financial` |
| [technical-signal](../skills/qmt-bridge-technical-signal/SKILL.md) | `formula_check` |

### 实时、日历与品种 ✅

| Skill | 脚本 |
|-------|------|
| [realtime-monitor](../skills/qmt-bridge-realtime-monitor/SKILL.md) | `ws_subscribe` |
| [event-calendar](../skills/qmt-bridge-event-calendar/SKILL.md) | `calendar_check` |
| [credit-margin](../skills/qmt-bridge-credit-margin/SKILL.md) | `credit_snapshot` |
| [etf](../skills/qmt-bridge-etf/SKILL.md) | `etf_snapshot` |
| [convertible](../skills/qmt-bridge-convertible/SKILL.md) | `cb_snapshot` |
| [option](../skills/qmt-bridge-option/SKILL.md) | `option_chain_snapshot` |
| [hk-connect](../skills/qmt-bridge-hk-connect/SKILL.md) | `hk_universe` |

## 安全提示

- 实盘下单、撤单、调仓、清仓须 **用户确认** 且脚本加 `--execute --confirm`
- **下载财报**（`financial-download`）会写服务端缓存，大批量前须说明
- **板块排序**（`sector-rank`）对大板块默认仅扫描前 800 只成分；用 `--list-sectors` 查有效板块名
- 研究脚本只读，不替代投资建议
- 勿泄露完整 API Key

## 冒烟测试

```bash
pytest tests/test_skills_smoke.py -q
```
