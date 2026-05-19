# Agent Skills

QMT Bridge 在 [`skills/`](../skills/) 提供 **20 个 Agent Skills**，均已配套可执行 Python 脚本与 [`justfile`](../justfile) 中的 `just agent-*` 快捷命令。

**路线图**：[skills/ROADMAP.md](../skills/ROADMAP.md) · **总览**：[skills/README.md](../skills/README.md) · **just 命令**：[开发与 just](development.md)

## 环境准备

1. 安装项目：`pip install -e .`（或 `just install-all`）
2. 复制配置：`cp .env.example .env`
3. 启用交易相关 Skill 时配置：
   - `QMT_BRIDGE_API_KEY`
   - `QMT_BRIDGE_TRADING_ACCOUNT_ID`（可选）
4. Bridge 已启动且 QMT 已登录（`just serve` 或 `qmt-server --trading ...`）

!!! tip "客户端连接地址"
    `.env` 中 `QMT_BRIDGE_HOST=0.0.0.0` 仅用于**服务端监听**。在本机跑 Agent 脚本时请用 **`127.0.0.1`**，或在命令行传 `--host 127.0.0.1`，不要用 `0.0.0.0` 作为客户端目标地址。

```bash
# 示例（端口与 .env 一致）
just agent-trading-status --host 127.0.0.1 --port 8080 --api-key YOUR_KEY
```

Windows 终端中文乱码：`chcp 65001` 或 `set PYTHONIOENCODING=utf-8`。

## 快速开始

```bash
pip install -e .

# 交易状态
just agent-trading-status --host 127.0.0.1 --port 8080 --api-key YOUR_KEY

# 当日盈亏（表格：账户概览 + 分标的拆解）
just agent-daily-pnl --host 127.0.0.1 --port 8080 --api-key YOUR_KEY

# 当日复盘、自选快照
just agent-daily-report --host 127.0.0.1 --port 8080 --api-key YOUR_KEY
just agent-watchlist --host 127.0.0.1 --port 8080 --codes 300394.SZ,688008.SH
```

无 [just](https://github.com/casey/just) 时，直接调用脚本（路径见各 Skill 的 `SKILL.md`）：

```bash
python skills/qmt-bridge-daily-pnl/scripts/daily_pnl_snapshot.py \
  --host 127.0.0.1 --port 8080 --api-key YOUR_KEY
```

## 提示词怎么用

1. **自然语言**：直接说下表「提示词示例」中的句子（可复制，按需改代码/数量）。
2. **@ Skill**：`@skills/qmt-bridge-daily-pnl/SKILL.md` 等。
3. **命令行**：`just agent-*` 或 `python skills/.../scripts/*.py`。

写操作须用户确认，脚本加 `--execute --confirm`。仓库内同源表格：[skills/README.md](../skills/README.md)。

## 全部 Skills（含提示词）

| Skill | 说明 | just 示例 | 提示词示例 |
|-------|------|-----------|------------|
| [qmt-bridge-trading](../skills/qmt-bridge-trading/SKILL.md) | 下单、清仓、状态 | `agent-trading-status` | `帮我查持仓和可用资金` · `用 Bridge 下一笔买入（先预览）` · `清仓某只股票` |
| [qmt-bridge-execution-review](../skills/qmt-bridge-execution-review/SKILL.md) | 当日复盘 | `agent-daily-report` | `生成今日交易复盘` · `汇总今天委托和成交` · `看看执行质量和滑点` |
| [qmt-bridge-portfolio-risk](../skills/qmt-bridge-portfolio-risk/SKILL.md) | 组合风险 | `agent-portfolio-risk` | `组合风险快照` · `持仓集中度是否过高` · `下单前现金够不够、有没有 T+1` |
| [qmt-bridge-daily-pnl](../skills/qmt-bridge-daily-pnl/SKILL.md) | 当日盈亏 | `agent-daily-pnl` | `今天账户盈亏多少` · `分标的列当日盈亏表` · `包含今天买卖和已清仓的盈亏` |
| [qmt-bridge-order-ops](../skills/qmt-bridge-order-ops/SKILL.md) | 查单、撤单 | `agent-list-orders` | `查今日委托和可撤单` · `撤销 order_id 为 xxx 的委托` |
| [qmt-bridge-return-analysis](../skills/qmt-bridge-return-analysis/SKILL.md) | 累计涨幅/概率 | `agent-return-analysis` | `1/5/10/30日涨幅多少` · `近10日K线上涨概率` |
| [qmt-bridge-market-watch](../skills/qmt-bridge-market-watch/SKILL.md) | 自选快照 | `agent-watchlist` | `自选行情快照` · `盘前看下指数和自选涨跌` |
| [qmt-bridge-sector-theme](../skills/qmt-bridge-sector-theme/SKILL.md) | 板块排序 | `agent-sector-rank` | `板块内涨幅排名` · `今天行业强弱怎么排` |
| [qmt-bridge-financial-download](../skills/qmt-bridge-financial-download/SKILL.md) | 下载财报 | `agent-download-financial` | `下载财报到 Bridge 缓存` · `补全这几只股票的财务数据` |
| [qmt-bridge-fundamental-screen](../skills/qmt-bridge-fundamental-screen/SKILL.md) | 财报筛选 | `agent-screen-financial` | `按 ROE、EPS 做基本面筛选` · `财报排雷` |
| [qmt-bridge-technical-signal](../skills/qmt-bridge-technical-signal/SKILL.md) | 公式检查 | `agent-formula-check` | `用 QMT 公式检查是否金叉` · `列出可用指标/公式` |
| [qmt-bridge-smart-execution](../skills/qmt-bridge-smart-execution/SKILL.md) | 下单预览 | `agent-execution-preview` | `预览这笔买单会不会涨跌停` · `限价还是市价更合适` |
| [qmt-bridge-rebalance](../skills/qmt-bridge-rebalance/SKILL.md) | 再平衡 | `agent-rebalance` | `按目标权重生成调仓计划` · `组合再平衡要买卖多少` |
| [qmt-bridge-credit-margin](../skills/qmt-bridge-credit-margin/SKILL.md) | 两融快照 | `agent-credit-snapshot` | `查两融保证金和担保品` |
| [qmt-bridge-realtime-monitor](../skills/qmt-bridge-realtime-monitor/SKILL.md) | WS 示例 | `agent-ws-subscribe` | `WebSocket 订阅实时行情` · `盘中推送成交回报` |
| [qmt-bridge-event-calendar](../skills/qmt-bridge-event-calendar/SKILL.md) | 交易日历 | `agent-calendar` | `今天是不是交易日` · `下一个交易日是哪天` |
| [qmt-bridge-etf](../skills/qmt-bridge-etf/SKILL.md) | ETF | `agent-etf-snapshot` | `查 ETF 列表和申赎清单` |
| [qmt-bridge-convertible](../skills/qmt-bridge-convertible/SKILL.md) | 可转债 | `agent-cb-snapshot` | `可转债列表和条款快照` |
| [qmt-bridge-option](../skills/qmt-bridge-option/SKILL.md) | 期权链 | `agent-option-chain` | `查 510050 期权链` · `认沽认购合约有哪些` |
| [qmt-bridge-hk-connect](../skills/qmt-bridge-hk-connect/SKILL.md) | 港股通 | `agent-hk-universe` | `港股通标的有哪些` · `沪港通深港通名单` |

## 推荐工作流

```
calendar → watchlist / sector-rank
    → download-financial → fundamental-screen
    → portfolio-risk → daily-pnl → execution-preview
    → trading → order-ops → daily-report
```

| 阶段 | just 命令 | 说明 | 提示词示例 |
|------|-----------|------|------------|
| 日历 | `agent-calendar` | 是否交易日 | `今天是不是交易日` |
| 强弱 | `agent-return-analysis` / `agent-watchlist` | 阶段涨幅、自选 | `N日累计涨幅` · `涨跌概率` |
| 看盘 | `agent-sector-rank` | 板块 | `板块内涨幅排名` |
| 研究 | `agent-download-financial` / `agent-screen-financial` | 财报 | `下载财报到 Bridge 缓存` · `按 ROE、EPS 做基本面筛选` |
| 风控 | `agent-portfolio-risk` | 集中度、现金 | `组合风险快照` · `下单前现金够不够` |
| 盈亏 | `agent-daily-pnl` | 当日盈亏表 | `今天账户盈亏多少` · `分标的列当日盈亏表` |
| 执行 | `agent-execution-preview` → `agent-place-order` | 预览后下单 | `预览这笔买单` · `用 Bridge 下一笔买入（先预览）` |
| 复盘 | `agent-daily-report` | 委托/成交 | `生成今日交易复盘` |

## 当日盈亏（daily-pnl）

Skill：[qmt-bridge-daily-pnl](../skills/qmt-bridge-daily-pnl/SKILL.md)

结合 **当前持仓**、**昨仓** 与 **当日成交**（含已清仓标的），输出表格化报告：

- **账户概览**：总资产、持仓市值、现金、成交笔数、当日盈亏合计
- **个股表**：代码、名称、状态、持仓/昨仓、现价、涨跌幅、市值、买卖量、昨仓/今买/今卖盈亏、当日盈亏

**估算公式**（无 QMT `today_profit_loss` 时）：

```
当日盈亏 = 现市值 − 昨收×昨仓 − 今日买入金额 + 今日卖出金额
```

| 参数 | 说明 |
|------|------|
| `--json` | JSON 输出（含 `symbols` / `cleared`） |
| `--no-detail` | 个股表隐藏昨仓/今买/今卖列 |
| `--no-tick-fallback` | 仅用柜台字段，不用行情估算 |
| `--min-pnl 500` | 仅显示 \|当日盈亏\| ≥ 500 的标的 |

优先使用 QMT 返回的 `today_profit_loss`；与柜台可能有手续费等细微差异。

## 分类索引（脚本）

完整列表与提示词见上表。按类别对应的 Python 脚本：

| 类别 | Skill | 脚本 |
|------|-------|------|
| 交易与执行 | trading | `trading_status`, `place_order`, `liquidate` |
| | order-ops | `list_orders`, `cancel_orders` |
| | smart-execution | `execution_preview` |
| | rebalance | `rebalance_plan` |
| 风控与复盘 | portfolio-risk | `portfolio_snapshot` |
| | daily-pnl | `daily_pnl_snapshot` |
| | execution-review | `daily_trade_report` |
| 研究 | return-analysis / market-watch | `return_probability_analysis`, `watchlist_snapshot` |
| | sector-theme | `sector_rank` |
| | financial-download | `download_financial_data` |
| | fundamental-screen | `screen_financial` |
| | technical-signal | `formula_check` |
| 实时/日历/品种 | realtime-monitor | `ws_subscribe` |
| | event-calendar | `calendar_check` |
| | credit-margin | `credit_snapshot` |
| | etf / convertible / option / hk-connect | `etf_snapshot`, `cb_snapshot`, `option_chain_snapshot`, `hk_universe` |

## 安全提示

- 实盘下单、撤单、调仓、清仓须 **用户确认** 且脚本加 `--execute --confirm`
- **下载财报**（`financial-download`）会写服务端缓存，大批量前须说明
- **板块排序**（`sector-rank`）对大板块默认仅扫描前 800 只成分；用 `--list-sectors` 查有效板块名
- 研究类与 **daily-pnl** 为只读，不替代投资建议
- 勿泄露完整 API Key

## 冒烟测试

```bash
just test
# 或仅 Skill 脚本导入检查
pytest tests/test_skills_smoke.py -q
```
