# QMT Trading Skill

> **QMT Trading Skill** = **QMT Bridge**（HTTP/WebSocket API）+ **Agent Skills**（自然语言工作流）。在 Windows 上对接 miniQMT，在 Mac/Linux 上用对话完成行情、交易、复盘与报告同步。

**QMT Bridge** 是其中的 API 服务层：封装 [xtquant](https://dict.thinktrader.net/nativeApi/start_now.html)（miniQMT 的 Python 库），将行情与交易以标准 HTTP/WebSocket 端点暴露；运行于 QMT 客户端旁的 Windows 机器，供局域网内任意设备访问。

```
Mac / Linux (主力机)                    Windows (中转站)
┌──────────────────────┐                ┌─────────────────────────┐
│  Agent / 分析代码       │   HTTP/WS     │  miniQMT 客户端 (登录中)  │
│  本地数据库            │ ◄───────────► │  QMT Bridge (FastAPI)    │
│  可视化仪表盘          │   局域网       │  xtquant                 │
└──────────────────────┘                └─────────────────────────┘
         ▲
         │ 自然语言触发 skills/*.py
         └─ QMT Trading Skill（21 个 Agent Skills）
```

## 核心特性

- **QMT Bridge** — 100+ REST API、5 个 WebSocket；历史 K 线、L2、板块、财务、期权、可转债、ETF、港股通、期货、程序化交易等
- **Agent Skills** — 21 个 Skill，自然语言或 `@` 触发（当日盈亏、交易复盘、组合风险、涨跌概率、飞书同步等）
- **零依赖客户端** — `QMTClient` 基于 stdlib，跨平台调用 Bridge
- **API Key 认证** — 交易端点可强制认证

## 快速导航

| 文档 | 说明 |
|------|------|
| [快速开始](getting-started.md) | 安装、配置、启动 Bridge |
| [配置参考](configuration.md) | Bridge 环境变量与 CLI |
| [开发指南](development.md) | pip / pytest / 脚本路径速查 |
| [Agent Skills](agent-skills.md) | Skill 列表、**提示词示例**、工作流 |
| [每日复盘报告示例](examples/daily-eval-report.md) | 复盘+飞书 Markdown 结构示例（金额已脱敏） |
| [REST API 速查](rest-api.md) | Bridge HTTP 端点列表 |
| [WebSocket](websocket.md) | Bridge WebSocket 端点 |
| [Python 客户端 API](api/index.md) | `QMTClient` 参考 |

## 安装

```bash
git clone https://github.com/atorber/qmt-trading-skill.git
cd qmt-trading-skill

# 安装服务端（含 WebSocket 支持）
pip install -e ".[full]"

# 或者只安装客户端（零依赖）
pip install -e .

# 含 WebSocket 订阅支持
pip install -e ".[client]"
```

## 许可

[MIT](https://github.com/atorber/qmt-trading-skill/blob/main/LICENSE)
