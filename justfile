# QMT Bridge — 项目快捷命令
# 使用: just <命令>  |  just --list 查看所有命令

# Windows 下使用 PowerShell 作为默认 shell
set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]

# 默认命令：列出所有可用命令
default:
    @just --list

# ─────────────────────────── 安装 ───────────────────────────

# 安装项目（仅客户端，零依赖）
install:
    pip install -e .

# 安装服务端全部依赖
install-server:
    pip install -e ".[full]"

# 安装文档依赖
install-docs:
    pip install -e ".[docs]"

# 安装仪表盘依赖
install-dashboard:
    pip install -e ".[dashboard]"

# 安装全部依赖（服务端 + 文档 + 仪表盘）
install-all:
    pip install -e ".[full,docs,dashboard]"

# ─────────────────────────── 服务 ───────────────────────────

# 启动 API 服务（前台，Ctrl+C 停止）
serve *ARGS:
    qmt-server {{ARGS}}

# 启动 API 服务（指定端口）
serve-port port="8000":
    qmt-server --port {{port}}

# 启动 API 服务（调试模式）
serve-debug:
    qmt-server --log-level debug

# 启动定时下载调度器（独立进程，与 serve 分开运行）
scheduler *ARGS:
    qmt-scheduler {{ARGS}}

# 启动定时下载调度器（调试模式）
scheduler-debug:
    qmt-scheduler --log-level debug

# 停止 API 服务（查找并终止占用 18888 端口的进程）
serve-stop:
    @echo "正在查找 qmt-server 进程..."
    Get-NetTCPConnection -LocalPort 18888 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }; if ($?) { echo "✅ qmt-server 已停止" } else { echo "⚠️ 未找到运行中的 qmt-server" }

# ─────────────────────────── 数据下载 ─────────────────────────

# 下载 A 股历史行情 + 财务数据（逐股精准增量，首次自动全量）
download-all *ARGS:
    python scripts/download_all.py {{ARGS}}

# 仅下载 1m K 线数据（跳过财务数据）
download-1m *ARGS:
    python scripts/download_all.py --periods 1m --skip-financial {{ARGS}}

# 下载最近两年的 1m K 线数据（快速启动算法开发）
download-1m-recent *ARGS:
    python scripts/download_all.py --periods 1m --skip-financial --since 2025 {{ARGS}}

# 仅下载 5m K 线数据（跳过财务数据）
download-5m *ARGS:
    python scripts/download_all.py --periods 5m --skip-financial {{ARGS}}

# 下载最近两年的 5m K 线数据（快速启动算法开发）
download-5m-recent *ARGS:
    python scripts/download_all.py --periods 5m --skip-financial --since 2025 {{ARGS}}

# ─────────────────────────── Agent 交易脚本 ─────────────────

# 交易状态摘要（只读，需 .env 中 QMT_BRIDGE_API_KEY）
agent-trading-status *ARGS:
    python skills/qmt-bridge-trading/scripts/trading_status.py {{ARGS}}

# 单笔下单预览（加 --execute --confirm 实盘提交）
agent-place-order *ARGS:
    python skills/qmt-bridge-trading/scripts/place_order.py {{ARGS}}

# 清仓预览（加 --execute --confirm 实盘提交）
agent-liquidate *ARGS:
    python skills/qmt-bridge-trading/scripts/liquidate.py {{ARGS}}

# 当日交易复盘（只读）
agent-daily-report *ARGS:
    python skills/qmt-bridge-execution-review/scripts/daily_trade_report.py {{ARGS}}

# 组合风险快照（只读）
agent-portfolio-risk *ARGS:
    python skills/qmt-bridge-portfolio-risk/scripts/portfolio_snapshot.py {{ARGS}}

# 当日盈亏快照（只读）
agent-daily-pnl *ARGS:
    python skills/qmt-bridge-daily-pnl/scripts/daily_pnl_snapshot.py {{ARGS}}

# 查询当日委托（只读）
agent-list-orders *ARGS:
    python skills/qmt-bridge-order-ops/scripts/list_orders.py {{ARGS}}

# 撤单预览（加 --execute --confirm 提交）
agent-cancel-orders *ARGS:
    python skills/qmt-bridge-order-ops/scripts/cancel_orders.py {{ARGS}}

# 多周期累计涨幅与涨跌概率（--codes 无需 Key；--holdings 需 API Key，缺 K 自动下载）
agent-return-analysis *ARGS:
    python skills/qmt-bridge-return-analysis/scripts/return_probability_analysis.py {{ARGS}}

# 自选行情快照（只读，无需 API Key）
agent-watchlist *ARGS:
    python skills/qmt-bridge-market-watch/scripts/watchlist_snapshot.py {{ARGS}}

# 板块成分涨跌排序（只读）
agent-sector-rank *ARGS:
    python skills/qmt-bridge-sector-theme/scripts/sector_rank.py {{ARGS}}

# 交易日历检查（只读）
agent-calendar *ARGS:
    python skills/qmt-bridge-event-calendar/scripts/calendar_check.py {{ARGS}}

# 下载财报到服务端缓存（写操作，建议 --verify）
agent-download-financial *ARGS:
    python skills/qmt-bridge-financial-download/scripts/download_financial_data.py {{ARGS}}

# 基本面筛选（查询为主，缺数可自动下载）
agent-screen-financial *ARGS:
    python skills/qmt-bridge-fundamental-screen/scripts/screen_financial.py {{ARGS}}

# 公式/指标检查（只读）
agent-formula-check *ARGS:
    python skills/qmt-bridge-technical-signal/scripts/formula_check.py {{ARGS}}

# 下单执行预览（不提交）
agent-execution-preview *ARGS:
    python skills/qmt-bridge-smart-execution/scripts/execution_preview.py {{ARGS}}

# 再平衡计划（--execute --confirm 提交）
agent-rebalance *ARGS:
    python skills/qmt-bridge-rebalance/scripts/rebalance_plan.py {{ARGS}}

# 两融快照（只读）
agent-credit-snapshot *ARGS:
    python skills/qmt-bridge-credit-margin/scripts/credit_snapshot.py {{ARGS}}

# WebSocket 订阅示例
agent-ws-subscribe *ARGS:
    python skills/qmt-bridge-realtime-monitor/scripts/ws_subscribe.py {{ARGS}}

# ETF / 转债 / 期权 / 港股通（只读）
agent-etf-snapshot *ARGS:
    python skills/qmt-bridge-etf/scripts/etf_snapshot.py {{ARGS}}

agent-cb-snapshot *ARGS:
    python skills/qmt-bridge-convertible/scripts/cb_snapshot.py {{ARGS}}

agent-option-chain *ARGS:
    python skills/qmt-bridge-option/scripts/option_chain_snapshot.py {{ARGS}}

agent-hk-universe *ARGS:
    python skills/qmt-bridge-hk-connect/scripts/hk_universe.py {{ARGS}}

# ─────────────────────────── 仪表盘 ─────────────────────────

# 启动可视化仪表盘（http://localhost:8501）
dashboard:
    streamlit run dashboard/app.py

# ─────────────────────────── 文档 ───────────────────────────

# 使用官方 lark-cli 发布报告到飞书知识库（需 lark-cli auth login）
lark-publish-report *ARGS:
    python scripts/lark_publish_report.py {{ARGS}}

# 安装 lark-cli（官方 @larksuite/cli）
lark-install:
    npx @larksuite/cli@latest install

# 将 Markdown 报告上传为飞书云文档（旧：自研 API 脚本，推荐 lark-publish-report）
feishu-create-doc *ARGS:
    python scripts/feishu_create_doc.py {{ARGS}}

# 本地预览 MkDocs 文档站点（http://127.0.0.1:8001）
docs:
    mkdocs serve -a 127.0.0.1:8001

# 构建 MkDocs 静态站点到 site/
docs-build:
    mkdocs build -d site/

# pdoc 本地预览客户端 API（http://localhost:8002）
docs-pdoc:
    pdoc src/qmt_bridge/client/ -p 8002

# 一键构建 MkDocs + pdoc
docs-all:
    @echo "==> 构建 MkDocs 文档..."
    mkdocs build -d site/
    @echo "==> 构建 pdoc API 参考..."
    pdoc -o site/pdoc src/qmt_bridge/client/
    @echo "==> 完成！"
    @echo "    MkDocs: site/index.html"
    @echo "    pdoc:   site/pdoc/index.html"

# 清理文档构建产物
docs-clean:
    rm -rf site/

# ─────────────────────────── 测试 ───────────────────────────

# API 契约测试（mock xtquant，无需 QMT）
test *ARGS:
    python -m pytest tests/ {{ARGS}}

# 联调测试（真实 Bridge，默认 8080，需服务已启动）
test-live *ARGS:
    $env:QMT_BRIDGE_LIVE = "1"; python -m pytest tests/live -m live -v {{ARGS}}

# 运行测试（verbose）
test-v:
    python -m pytest tests/ -v

# ─────────────────────────── 代码质量 ───────────────────────

# 类型检查（需要 mypy）
typecheck:
    python -m mypy src/qmt_bridge/

# 格式化代码（需要 ruff）
fmt:
    python -m ruff format src/ tests/

# 代码检查（需要 ruff）
lint:
    python -m ruff check src/ tests/

# 格式化 + 检查
check: fmt lint

# ─────────────────────────── 构建 ───────────────────────────

# 构建 wheel 和 sdist
build:
    python -m build

# 发布到 TestPyPI（首次验证用）
publish-test: build
    python -m twine upload --repository testpypi dist/*

# 发布到 PyPI
publish: build
    python -m twine upload dist/*

# 清理构建产物
clean:
    rm -rf dist/ build/ site/ *.egg-info src/*.egg-info
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# ─────────────────────────── 信息 ───────────────────────────

# 显示项目版本
version:
    @python -c "from qmt_bridge._version import __version__; print(__version__)"
