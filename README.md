# QMT Bridge

> 将 miniQMT（xtquant）封装为 HTTP/WebSocket API，供局域网内任意语言调用。Agent Skills 工作流见独立仓库 [qmt-trading-skill](https://github.com/atorber/qmt-trading-skill)。

**在线文档**：[QMT Bridge 文档](https://atorber.github.io/qmt-bridge/)（push `main` 后由 GitHub Pages 发布）。

```
Mac / Linux / easy-auto                 Windows（与 QMT 同机）
┌──────────────────────┐                ┌─────────────────────────┐
│  QMTClient / HTTP    │   HTTP/WS     │  miniQMT 客户端（登录中）  │
│  Agent Skills        │ ◄───────────► │  qmt-server (本仓库)      │
└──────────────────────┘   局域网       │  xtquant                 │
                                       └─────────────────────────┘
```

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

验证：`http://127.0.0.1:8080/docs` 或 `GET /api/meta/health`。长期运行见 `scripts/pm2-start.bat`。

| 环境变量 | 默认 | 说明 |
|---------|------|------|
| `QMT_BRIDGE_HOST` | `0.0.0.0` | 监听地址 |
| `QMT_BRIDGE_PORT` | `8000` | 端口 |
| `QMT_BRIDGE_API_KEY` | 空 | 设置后交易端点须带 `X-API-Key` |
| `QMT_BRIDGE_TRADING_ENABLED` | `false` | 等同 `--trading` |

完整配置见 [docs/configuration.md](docs/configuration.md)。

## Python 客户端

```python
from qmt_bridge import QMTClient

client = QMTClient(host="127.0.0.1", port=8080, api_key="your-key")
snapshot = client.get_market_snapshot(["000001.SZ"])
```

账户解析（Skill / 自研脚本共用，不依赖 FastAPI）：

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

自然语言交易 / 复盘工作流请使用 [qmt-trading-skill](https://github.com/atorber/qmt-trading-skill)（开发时可 submodule 嵌套本仓库）。

## 许可

[MIT](LICENSE)
