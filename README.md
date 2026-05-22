# QMT Trading Skill

> 在 Cursor / Claude Code / CodeX / OpenClaw 中用**自然语言**完成 A 股行情查询、交易、当日盈亏、交易复盘与飞书报告同步——底层通过 **QMT Bridge** 对接 Windows 上的 miniQMT。

本仓库的核心是 **21 个 Agent Skills**（`skills/`）：每个 Skill 含 `SKILL.md` 规程与可执行 Python 脚本，由 Agent 读取后调用 Bridge API。**QMT Bridge** 是支撑层（HTTP/WebSocket 服务 + 可选 `QMTClient`），不是使用入口。

---

## 架构关系

三层自下而上依赖，职责分离：

```
┌─────────────────────────────────────────────────────────────────┐
│  QMT Trading Skill（本仓库 · 你主要与之交互）                      │
│  · 21 个 Agent Skills：自然语言 → scripts/*.py → Bridge API      │
│  · 工作流：盈亏 / 复盘 / 风控 / 研究 / 飞书同步 …                  │
└───────────────────────────────┬─────────────────────────────────┘
                                │ HTTP / WebSocket（局域网）
┌───────────────────────────────▼─────────────────────────────────┐
│  QMT Bridge（API 服务层 · `qmt-server`）                          │
│  · FastAPI：100+ REST、5 个 WebSocket                             │
│  · 封装 xtquant，把行情与交易暴露为标准端点                         │
└───────────────────────────────┬─────────────────────────────────┘
                                │ 进程内调用
┌───────────────────────────────▼─────────────────────────────────┐
│  QMT / miniQMT（券商客户端 · 仅 Windows）                         │
│  · 需登录并保持运行；xtquant 依赖此进程获取行情与报单               │
└─────────────────────────────────────────────────────────────────┘
```

| 层级 | 运行位置 | 你需要做什么 |
|------|----------|--------------|
| **QMT** | Windows | 安装券商 QMT，勾选「独立交易」登录，保持窗口运行 |
| **QMT Bridge** | Windows（与 QMT 同机） | 安装本仓库、`qmt-server` 启动 API（交易需 `--trading`） |
| **QMT Trading Skill** | Mac / Linux / Windows（主力机） | Cursor 对话或 `@` Skill；Agent 执行 `skills/*/scripts/*.py` |

典型拓扑：Windows 作**中转站**（QMT + Bridge），Mac/Linux 作**主力机**（对话 + 分析 + 数据库）；Skill 脚本通过局域网 IP 访问 Bridge。

```
Mac / Linux（主力机）                 Windows（中转站）
┌──────────────────────┐             ┌─────────────────────────┐
│ Cursor / Claude      │   HTTP/WS   │  QMT 客户端（登录中）      │
│ @skills/…/SKILL.md   │ ◄─────────► │  qmt-server (Bridge)     │
│ 分析 / 本地库         │   局域网     │  xtquant                 │
└──────────────────────┘             └─────────────────────────┘
         ▲
         └── QMT Trading Skill：自然语言触发脚本
```

---

## Skill 能做什么

Skills 把重复性的 Bridge 调用封装成**可对话、可审计**的工作流。写操作（下单、撤单、调仓、下载财报）须你确认后脚本才加 `--execute --confirm`。

### 按场景分类

| 场景 | Skill | 典型说法 |
|------|-------|----------|
| **交易** | [trading](skills/qmt-bridge-trading/SKILL.md) | `帮我查持仓和可用资金` · `下一笔买入（先预览）` · `清仓某只股票` |
| | [order-ops](skills/qmt-bridge-order-ops/SKILL.md) | `查今日委托和可撤单` · `撤销 order_id 为 xxx 的委托` |
| | [smart-execution](skills/qmt-bridge-smart-execution/SKILL.md) | `预览这笔买单会不会涨跌停` |
| | [rebalance](skills/qmt-bridge-rebalance/SKILL.md) | `按目标权重生成调仓计划` |
| **复盘与报告** | [**daily-pnl**](skills/qmt-bridge-daily-pnl/SKILL.md) | `今天账户盈亏多少` · `分标的列当日盈亏` |
| | [execution-review](skills/qmt-bridge-execution-review/SKILL.md) | `今日操作评估` · `交易复盘+执行质量` · `评价今天买卖是否合理` |
| | [feishu-doc](skills/qmt-bridge-feishu-doc/SKILL.md) | `把今日复盘同步到飞书` · `上传涨跌分析到飞书` |
| **风控** | [portfolio-risk](skills/qmt-bridge-portfolio-risk/SKILL.md) | `组合风险快照` · `持仓集中度是否过高` |
| **研究** | [**return-analysis**](skills/qmt-bridge-return-analysis/SKILL.md) | `评估持仓涨幅概率` · `1/5/10/30 日阶段强弱` |
| | [market-watch](skills/qmt-bridge-market-watch/SKILL.md) | `自选行情快照` · `盘前看下指数和自选涨跌` |
| | [sector-theme](skills/qmt-bridge-sector-theme/SKILL.md) | `今天行业强弱怎么排` |
| | [financial-download](skills/qmt-bridge-financial-download/SKILL.md) | `下载财报到 Bridge 缓存` |
| | [fundamental-screen](skills/qmt-bridge-fundamental-screen/SKILL.md) | `按 ROE、EPS 做基本面筛选` |
| | [technical-signal](skills/qmt-bridge-technical-signal/SKILL.md) | `用 QMT 公式检查是否金叉` |
| **品种扩展** | [etf](skills/qmt-bridge-etf/SKILL.md)、[convertible](skills/qmt-bridge-convertible/SKILL.md)、[option](skills/qmt-bridge-option/SKILL.md)、[hk-connect](skills/qmt-bridge-hk-connect/SKILL.md) | ETF / 可转债 / 期权链 / 港股通 |
| **其他** | [realtime-monitor](skills/qmt-bridge-realtime-monitor/SKILL.md)、[event-calendar](skills/qmt-bridge-event-calendar/SKILL.md)、[credit-margin](skills/qmt-bridge-credit-margin/SKILL.md) | WebSocket 示例、交易日历、两融快照 |

完整列表、提示词与路线图：[`skills/README.md`](skills/README.md) · [`skills/ROADMAP.md`](skills/ROADMAP.md) · 在线 [Agent Skills 文档](docs/agent-skills.md)。

### 推荐日内工作流

```
calendar → watchlist / sector-rank
    → download-financial → fundamental-screen
    → return-analysis → portfolio-risk → daily-pnl
    → execution-review → feishu-doc
```

复盘报告示例（脱敏）：[`docs/examples/daily-eval-report.md`](docs/examples/daily-eval-report.md)。

### 亮点能力说明

- **当日盈亏**（`daily-pnl`）：优先采用柜台 `today_profit_loss`；否则按现市值、昨收、当日买卖估算，含已清仓标的；支持 `--json`。
- **交易复盘**（`execution-review`）：汇总成交与持仓变动，结合量能/热度与交易哲学做操作评价；`--feishu-md` 生成飞书 Markdown。
- **涨跌概率**（`return-analysis`）：多周期累计涨幅与量价形态统计，可对接持仓列表输出明日观察点。
- **飞书同步**（`feishu-doc`）：按 [`doc-registry`](skills/qmt-bridge-feishu-doc/references/doc-registry.md) 命名规则上传云文档，工作流见 [daily-eval-sync](skills/qmt-bridge-feishu-doc/references/workflows/daily-eval-sync.md)。

---

## 部署与使用

分两步：**先让 Bridge 在 Windows 上可用**，**再在主力机用 Skills**。

### 环境要求

| 端 | 要求 |
|----|------|
| **Windows（Bridge）** | Python 3.10+、QMT 客户端（已开通 miniQMT）、xtquant（通常随 QMT 安装） |
| **主力机（Skills）** | 安装本仓库 `pip install -e .`；[Cursor](https://cursor.com) 或 Claude Code；与 Windows **同一局域网** |
| **网络** | 防火墙放行 Bridge 端口（默认 `8000`，常用 `8080`） |

### 第一步：安装与配置（Windows）

```bash
git clone https://github.com/atorber/qmt-trading-skill.git
cd qmt-trading-skill
pip install -e ".[full]"

cp .env.example .env
# 编辑 .env：端口、API Key、交易路径等
```

### 第二步：启动 QMT 与 Bridge（Windows）

1. 打开 **QMT**，勾选 **「独立交易」** 登录，保持运行（可最小化）。
2. 启动 API 服务：

```bash
# 仅行情数据
qmt-server --port 8080

# 启用交易（Skill 下单/查持仓需要）
qmt-server --port 8080 --trading --api-key your-secret-key \
  --mini-qmt-path "C:\你的QMT路径\userdata_mini" \
  --account-id 你的资金账号
```

也可使用 `scripts/start.bat` / `scripts/start.sh`（见 [`scripts/`](scripts/)）。

3. **验证**：浏览器打开 `http://127.0.0.1:8080/docs`，或：

```bash
curl http://127.0.0.1:8080/api/meta/health
```

常用环境变量见下表；完整说明见 [配置参考](docs/configuration.md)。

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `QMT_BRIDGE_HOST` | `0.0.0.0` | 监听地址（允许局域网访问） |
| `QMT_BRIDGE_PORT` | `8000` | 端口（示例多用 `8080`） |
| `QMT_BRIDGE_API_KEY` | _(空)_ | 设置后交易端点须带 `X-API-Key` |
| `QMT_BRIDGE_TRADING_ENABLED` | `false` | 等同 `--trading` |

### 第三步：在 Cursor 使用 Trading Skill（主力机）

1. **克隆同一仓库**（或仅复制 `skills/` 与 `.env`），`pip install -e .`。
2. 在 `.env` 中配置与 Windows Bridge 一致的 `QMT_BRIDGE_API_KEY`、`QMT_BRIDGE_PORT`；脚本连接地址用 **`127.0.0.1`**（本机调 Bridge）或 **Windows 局域网 IP**（远程调 Bridge），不要用 `0.0.0.0`。
3. **自然语言**：在对话中直接说，例如：
   - `今天账户盈亏多少`
   - `生成今日交易复盘`
   - `把复盘同步到飞书`
4. **@ Skill 文件**：`@skills/qmt-bridge-execution-review/SKILL.md`，让 Agent 按规程执行脚本。

**在 Cursor 中启用 Skills 目录（可选）：**

```bash
mkdir -p .cursor/skills
for d in skills/qmt-bridge-*/; do
  name=$(basename "$d")
  ln -sf "../../skills/$name" ".cursor/skills/$name"
done
```

**本机手动跑脚本（调试 / 无 Agent 时）：**

```bash
# 仓库根目录，.env 已配置 QMT_BRIDGE_API_KEY
python skills/qmt-bridge-daily-pnl/scripts/daily_pnl_snapshot.py \
  --host 127.0.0.1 --port 8080 --api-key YOUR_KEY

python skills/qmt-bridge-execution-review/scripts/daily_trade_report.py \
  --host 127.0.0.1 --port 8080 --api-key YOUR_KEY --feishu-md
```

Windows 终端中文乱码：`chcp 65001` 或 `$env:PYTHONIOENCODING='utf-8'`。

### 可选：仪表盘与 Python 客户端

- **Streamlit 仪表盘**：`pip install -e ".[dashboard]" && streamlit run dashboard/app.py`（连接 Bridge 做可视化，非 Skill 入口）。
- **`QMTClient`**：零依赖 HTTP 客户端，适合自写策略代码直连 Bridge；示例见 [快速开始 · Python 客户端](docs/getting-started.md#python-客户端用法)。

---

## QMT Bridge（支撑层速览）

Bridge 为 Skills 与自定义程序提供统一 API，启动后自动预下载板块、日历、指数权重等基础数据（每 24 小时刷新）。你通常**无需**逐条记忆 REST 路径——交给 Skill 或查阅在线文档即可。

| 能力 | 说明 |
|------|------|
| 行情 | 历史/实时 K 线、L2、板块、财务、指数权重 |
| 品种 | 期权链、可转债、ETF、港股通、期货主力 |
| 交易 | 下单、撤单、批量委托、融资融券、银证转账（须 API Key） |
| 实时 | 5 个 WebSocket：行情、全市场、L2 千档、下载进度、交易回报 |

- **交互式 API 文档**：服务运行后访问 `/docs`（Swagger）或 `/redoc`
- **完整端点列表**：[API 文档](docs/api/index.md) · [WebSocket](docs/websocket.md)
- **实时 K 线模式**：REST 拉历史 + WebSocket 推增量，见 [文档](docs/websocket.md)

---

## 文档

| 文档 | 说明 |
|------|------|
| [快速开始](docs/getting-started.md) | Bridge 安装、配置、验证与客户端示例 |
| [Agent Skills](docs/agent-skills.md) | 21 个 Skill 在线说明 |
| [配置参考](docs/configuration.md) | 环境变量与 CLI 参数 |
| [开发指南](docs/development.md) | 贡献、测试、Skill 开发约定 |
| **GitHub Pages** | push `main` 后自动发布；示例：<https://atorber.github.io/qmt-trading-skill/> |

本地预览：`pip install -e ".[docs]" && mkdocs serve -a 127.0.0.1:8001`

---

## 项目结构

```
qmt-bridge/
├── skills/                    # ★ QMT Trading Skill 核心
│   ├── README.md              # Skill 列表与提示词
│   ├── ROADMAP.md             # 实现状态
│   ├── _shared/               # 公共模块（pnl、飞书、表格等）
│   └── qmt-bridge-*/          # 各 Skill：SKILL.md + scripts/
├── src/qmt_bridge/
│   ├── server/                # QMT Bridge：FastAPI + qmt-server
│   └── client/                # QMTClient（可选，直连 API）
├── dashboard/                 # Streamlit 仪表盘（可选）
├── docs/                      # MkDocs 文档
├── scripts/                   # 启动/停止 Bridge
└── tests/                     # API 契约测试 + Skill smoke
```

---

## 测试

```bash
pip install -e ".[server,test]"
python -m pytest tests/ -q                    # 契约测试（无需 QMT）
pytest tests/test_skills_smoke.py -q          # Skill 脚本 smoke
```

联调真实 Bridge：`tests/README.md`（设置 `QMT_BRIDGE_LIVE=1` 等）。

---

## 安全说明

设计用于**可信局域网**。请勿将 Bridge 直接暴露公网；远程访问请用 VPN。交易端点建议始终配置 `QMT_BRIDGE_API_KEY`。

---

## FAQ

**Q: 必须一直开着 QMT 吗？**  
是的。实时行情与报单依赖 QMT 进程；历史缓存可在客户端关闭后通过 `local_data` 等只读接口访问。

**Q: Mac 上能直接跑 xtquant 吗？**  
不能。miniQMT 仅 Windows；Mac/Linux 通过 Skills 对话 + 局域网访问 Windows 上的 Bridge。

**Q: 不用 Cursor，能用 Skills 吗？**  
可以。每个 Skill 的 `SKILL.md` 中有 `python skills/.../scripts/....py` 命令，在仓库根目录配置 `.env` 后直接运行。

**Q: Bridge 和 Skill 端口不一致怎么办？**  
以 `.env` 的 `QMT_BRIDGE_PORT` 为准；脚本加 `--port 8080`（或与 `qmt-server` 一致）。

**Q: API 细节在哪里？**  
运行中的 `/docs`，或 [docs/api/](docs/api/index.md)。README 以 Skill 工作流为主，不重复罗列全部端点。

---

## 感谢

本项目最初 fork 自 [atompilot/qmt-bridge](https://github.com/atompilot/qmt-bridge)，在此向原作者致以感谢与敬意。

## License

[MIT](LICENSE)
