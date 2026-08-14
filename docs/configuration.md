# 配置参考

**QMT Bridge** 支持通过 `.env` 文件、环境变量或 CLI 参数进行配置。优先级：**CLI 参数 > 环境变量 > .env 文件 > 默认值**。

## 配置项

| 环境变量 | CLI 参数 | 默认值 | 说明 |
|---------|---------|-------|------|
| `QMT_BRIDGE_HOST` | `--host` | `0.0.0.0` | 监听地址（`0.0.0.0` = 允许局域网访问） |
| `QMT_BRIDGE_PORT` | `--port` | `8000` | 监听端口 |
| `QMT_BRIDGE_LOG_LEVEL` | `--log-level` | `info` | 日志级别：`critical` / `error` / `warning` / `info` / `debug` |
| `QMT_BRIDGE_WORKERS` | `--workers` | `1` | Worker 数量（Windows 下建议保持 1） |
| `QMT_BRIDGE_API_KEY` | `--api-key` | _(空)_ | API Key，用于保护交易端点 |
| `QMT_BRIDGE_REQUIRE_AUTH_FOR_DATA` | — | `false` | 数据端点是否也要求认证 |
| `QMT_BRIDGE_TRADING_ENABLED` | `--trading` | `false` | 是否启用交易模块 |
| `QMT_BRIDGE_MINI_QMT_PATH` | `--mini-qmt-path` | _(空)_ | miniQMT 安装路径（交易模块需要） |
| `QMT_BRIDGE_STOCK_ACCOUNT_ID` | `--stock-account-id` | _(空)_ | 普通证券账户 ID |
| `QMT_BRIDGE_CREDIT_ACCOUNT_ID` | `--credit-account-id` | _(空)_ | 信用两融账户 ID |
| `QMT_BRIDGE_DEFAULT_ACCOUNT` | `--default-account` | `stock` | 默认 API/订阅账户：`stock` \| `credit` |

HTTP 客户端请连接 `127.0.0.1` 或本机局域网 IP，不要把服务端监听地址 `0.0.0.0` 当作请求目标。`.env.example` 里的端口可能与代码默认值 `8000` 不同，以你实际写入 `.env` 的值为准；[qmt-trading-skill](https://github.com/atorber/qmt-trading-skill) 的客户端 `.env` 必须与此一致。

## .env 文件示例

```bash
# QMT Bridge 配置
# 复制此文件为 .env 并按需修改:  cp .env.example .env

# 监听地址 (0.0.0.0 表示允许局域网访问)
QMT_BRIDGE_HOST=0.0.0.0

# 监听端口（代码默认 8000；与客户端 / Skill 保持一致）
QMT_BRIDGE_PORT=8000

# uvicorn 日志级别: critical/error/warning/info/debug
QMT_BRIDGE_LOG_LEVEL=info

# uvicorn worker 数量 (Windows 下建议保持 1)
QMT_BRIDGE_WORKERS=1

# API Key（用于保护交易端点，留空则交易端点不可用）
# QMT_BRIDGE_API_KEY=your-secret-api-key

# 是否要求数据端点也进行认证（默认否，仅交易端点需要认证）
# QMT_BRIDGE_REQUIRE_AUTH_FOR_DATA=false

# 是否启用交易模块（默认否）
# QMT_BRIDGE_TRADING_ENABLED=false

# miniQMT 安装路径（交易模块需要）
# QMT_BRIDGE_MINI_QMT_PATH=C:\国金QMT交易端\userdata_mini

# 普通证券账户
# QMT_BRIDGE_STOCK_ACCOUNT_ID=755100210127

# 信用两融账户
# QMT_BRIDGE_CREDIT_ACCOUNT_ID=755860001037

# 默认 API 账户：stock | credit
# QMT_BRIDGE_DEFAULT_ACCOUNT=stock
```

## 认证机制

QMT Bridge API 支持可选的 API Key 认证：

- **交易端点** (`/api/trading/*`, `/api/credit/*`, `/api/fund/*`, `/api/bank/*`, `/api/smt/*`) — 设置了 `API_KEY` 时强制认证
- **数据端点** — 默认无需认证，可通过 `QMT_BRIDGE_REQUIRE_AUTH_FOR_DATA=true` 开启
- **认证方式** — HTTP Header `X-API-Key: your-secret-key`
- **WebSocket 交易** — 查询参数 `?api_key=your-secret-key`

!!! warning "安全提示"
    本项目设计为**仅在可信局域网内使用**。请勿将服务直接暴露到公网。如确有需要，请通过 VPN 或防火墙规则保护访问。
