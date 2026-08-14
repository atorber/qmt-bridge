# QMT Bridge

> 将 miniQMT（xtquant）封装为 HTTP/WebSocket API，供局域网内任意语言调用。

**在线文档**：[QMT Bridge 文档](https://atorber.github.io/qmt-bridge/)

```
调用方（HTTP / QMTClient）               Windows（与 QMT 同机）
┌──────────────────────┐                ┌─────────────────────────┐
│  策略 / BFF / 脚本    │   HTTP/WS     │  miniQMT 客户端（登录中）  │
│                      │ ◄───────────► │  qmt-server (本仓库)      │
└──────────────────────┘   局域网       │  xtquant                 │
                                       └─────────────────────────┘
```

本仓库**只提供 API 与 Python 客户端**。自然语言交易 / 复盘工作流已迁至独立仓库 [qmt-trading-skill](https://github.com/atorber/qmt-trading-skill)（不再包含 `skills/`）。

## 安装

```bash
git clone https://github.com/atorber/qmt-bridge.git
cd qmt-bridge
pip install -e ".[full]"
cp .env.example .env
```

仅客户端（零依赖 stdlib）：`pip install qmt-bridge` 或 `pip install -e ".[client]"`。

## 启动

QMT 勾选「独立交易」登录并保持运行，然后：

```bash
qmt-server --port 8080

qmt-server --port 8080 --trading --api-key your-secret-key \
  --mini-qmt-path "C:\你的QMT路径\userdata_mini" \
  --stock-account-id 普通账户ID --credit-account-id 信用账户ID
```

代码默认端口 **8000**；若 `.env` 里改了 `QMT_BRIDGE_PORT`，客户端与 Skill 必须用同一端口。验证：`http://127.0.0.1:<端口>/docs` 或 `GET /api/meta/health`。长期运行见 `scripts/pm2-start.bat`。

完整配置见 [docs/configuration.md](docs/configuration.md)。

## Python 客户端

```python
from qmt_bridge import QMTClient

client = QMTClient(host="127.0.0.1", port=8080, api_key="your-key")
snapshot = client.get_market_snapshot(["000001.SZ"])
```

```python
from qmt_bridge.accounts import resolve_default_trading_account
```

## 文档

| 文档 | 说明 |
|------|------|
| [快速开始](docs/getting-started.md) | 安装、启动、客户端示例 |
| [REST API](docs/rest-api.md) | HTTP 参数与响应 |
| [WebSocket](docs/websocket.md) | 实时推送 |
| [Python 客户端](docs/api/index.md) | `QMTClient` |

## 许可

[MIT](LICENSE)
