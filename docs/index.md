# QMT Bridge

> 将 miniQMT（xtquant）封装为 HTTP/WebSocket API。

```
调用方（HTTP / QMTClient）               Windows（与 QMT 同机）
┌──────────────────────┐                ┌─────────────────────────┐
│  QMTClient / HTTP    │   HTTP/WS     │  miniQMT 客户端           │
│                      │ ◄───────────► │  QMT Bridge (FastAPI)    │
└──────────────────────┘                └─────────────────────────┘
```

自然语言工作流见独立仓库 [qmt-trading-skill](https://github.com/atorber/qmt-trading-skill)。

## 核心特性

- 100+ REST API、多个 WebSocket
- `QMTClient` 零依赖（stdlib）
- 交易端点 API Key 认证

## 快速导航

| 文档 | 说明 |
|------|------|
| [快速开始](getting-started.md) | 安装、配置、启动 |
| [配置参考](configuration.md) | 环境变量与 CLI |
| [开发指南](development.md) | pytest / 贡献 |
| [REST API 速查](rest-api.md) | HTTP 端点、参数、响应 |
| [WebSocket](websocket.md) | 实时推送 |
| [Python 客户端 API](api/index.md) | `QMTClient` |

## 安装

```bash
git clone https://github.com/atorber/qmt-bridge.git
cd qmt-bridge
pip install -e ".[full]"
```

## 许可

[MIT](https://github.com/atorber/qmt-bridge/blob/main/LICENSE)
