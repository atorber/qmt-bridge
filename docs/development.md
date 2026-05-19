# 开发与 just

仓库根目录的 [`justfile`](../justfile) 用 [just](https://github.com/casey/just) 封装常用命令，避免记忆长串 `pip` / `python` / `pytest` 路径。安装 just 后，在仓库根目录执行：

```bash
just              # 列出所有命令（同 just --list）
just <命令名> [参数...]
```

未安装 just 时，打开 `justfile` 查看对应 recipe 中的实际命令并手动执行。

## 安装与依赖

| 命令 | 说明 |
|------|------|
| `just install` | `pip install -e .`（客户端） |
| `just install-server` | 服务端 `[full]` |
| `just install-docs` | MkDocs 文档依赖 |
| `just install-dashboard` | Streamlit 仪表盘 |
| `just install-all` | 上述全部 |

## 服务与数据

| 命令 | 说明 |
|------|------|
| `just serve` | 前台启动 `qmt-server`（可跟参数） |
| `just serve-port 8080` | 指定端口 |
| `just serve-debug` | debug 日志 |
| `just scheduler` | 独立进程定时下载 |
| `just serve-stop` | 停止占用默认端口的进程（Windows） |
| `just download-all` | 全量历史 + 财务下载 |
| `just download-1m` / `download-5m` | 指定周期 K 线 |

## Agent 脚本（`agent-*`）

均需 Bridge 已运行；交易类需 `.env` 中 `QMT_BRIDGE_API_KEY`。建议：

```bash
just agent-<名称> --host 127.0.0.1 --port 8080 --api-key YOUR_KEY
```

| 命令 | 只读 | 说明 | 提示词示例 |
|------|------|------|------------|
| `agent-trading-status` | 是 | 健康、持仓、资产 | `帮我查持仓和可用资金` |
| `agent-daily-pnl` | 是 | 当日盈亏表格 | `今天账户盈亏多少` · `分标的列当日盈亏表` |
| `agent-daily-report` | 是 | 委托/成交复盘 | `生成今日交易复盘` |
| `agent-portfolio-risk` | 是 | 组合风险 | `组合风险快照` |
| `agent-list-orders` | 是 | 当日委托 | `查今日委托和可撤单` |
| `agent-cancel-orders` | 预览 | 撤单 | `撤销 order_id 为 xxx 的委托` |
| `agent-place-order` | 预览 | 下单 | `用 Bridge 下一笔买入（先预览）` |
| `agent-liquidate` | 预览 | 清仓 | `清仓某只股票` |
| `agent-watchlist` | 是 | 自选/指数 | `自选行情快照` |
| `agent-sector-rank` | 是 | 板块排序 | `板块内涨幅排名` |
| `agent-calendar` | 是 | 交易日历 | `今天是不是交易日` |
| `agent-download-financial` | 写 | 下载财报 | `下载财报到 Bridge 缓存` |
| `agent-screen-financial` | 是 | 财报筛选 | `按 ROE、EPS 做基本面筛选` |
| `agent-formula-check` | 是 | 公式检查 | `用 QMT 公式检查是否金叉` |
| `agent-execution-preview` | 是 | 下单预览 | `预览这笔买单会不会涨跌停` |
| `agent-rebalance` | 预览 | 再平衡 | `按目标权重生成调仓计划` |
| `agent-credit-snapshot` | 是 | 两融 | `查两融保证金和担保品` |
| `agent-ws-subscribe` | 是 | WS 示例 | `WebSocket 订阅实时行情` |
| `agent-etf-snapshot` | 是 | ETF | `查 ETF 列表和申赎清单` |
| `agent-cb-snapshot` | 是 | 可转债 | `可转债列表和条款快照` |
| `agent-option-chain` | 是 | 期权链 | `查 510050 期权链` |
| `agent-hk-universe` | 是 | 港股通 | `港股通标的有哪些` |

完整 19 项见 [Agent Skills — 全部 Skills](agent-skills.md#全部-skills含提示词)。

## 文档、测试与构建

| 命令 | 说明 |
|------|------|
| `just docs` | MkDocs 本地预览 → <http://127.0.0.1:8001> |
| `just docs-build` | 构建静态站点到 `site/` |
| `just dashboard` | Streamlit 仪表盘 → :8501 |
| `just test` | pytest 契约测试（无需 QMT） |
| `just test-live` | 联调测试（需已启动 Bridge） |
| `just fmt` / `lint` / `check` | ruff 格式化与检查 |
| `just build` | 构建 wheel |
| `just clean` | 清理构建产物 |

## 飞书报告（可选）

| 命令 | 说明 |
|------|------|
| `just lark-install` | 安装官方 lark-cli |
| `just lark-publish-report` | 发布报告到飞书知识库 |
