# QMT Bridge

> 将 miniQMT（xtquant）封装为 HTTP/WebSocket API，供局域网内任意语言调用。

**在线文档**：[QMT Bridge 文档](https://atorber.github.io/qmt-bridge/)

```
调用方（HTTP / QMTClient）               Windows（与 QMT 同机）
┌──────────────────────┐                ┌─────────────────────────┐
│  策略 / BFF / 脚本    │   HTTP/WS     │  miniQMT 客户端（登录中）  │
│                      │ ◄───────────► │  qmt-server / 桌面面板    │
└──────────────────────┘   局域网       │  xtquant                 │
                                       └─────────────────────────┘
```

本仓库提供 **HTTP/WebSocket API**、**Python 客户端**，以及 Windows **桌面控制面板 / 免环境 CLI**。自然语言交易 / 复盘工作流见独立仓库 [qmt-trading-skill](https://github.com/atorber/qmt-trading-skill)（本仓不含 `skills/`）。

## 安装

### Windows 安装包 / 便携包（无需本机 Python）

从 [GitHub Releases](https://github.com/atorber/qmt-bridge/releases) 下载（连交易请优先 **x86-win**）：

| 文件 | 说明 |
|------|------|
| `QMTBridge-Setup-*-x86-win.exe` | 桌面控制面板安装包 |
| `QMTBridge-*-x86-win.zip` | 桌面便携版（含面板 + `qmt-server.exe`） |
| `QMTBridge-CLI-*-x86-win.zip` | **仅 CLI**：解压即可用 `qmt-server.exe` 启动服务 |
| `*-arm-win.*` | Windows ARM64 对应产物 |

本地打包：

```powershell
powershell -ExecutionPolicy Bypass -File packaging\windows\build.ps1 -Arch x64
```

详情见 [快速开始](docs/getting-started.md)。

### 开发者（pip）

```bash
git clone https://github.com/atorber/qmt-bridge.git
cd qmt-bridge
pip install -e ".[full]"
cp .env.example .env
```

仅客户端（零依赖 stdlib）：`pip install qmt-bridge-pro` 或 `pip install -e ".[client]"`。导入仍为 `from qmt_bridge import QMTClient`。

## 启动

客户机需先安装并登录券商 **miniQMT**（勾选「独立交易」并保持运行）。

### 桌面控制面板

安装或解压桌面包 → 双击 **QMT Bridge** → 确认端口 / 路径 → **启动**。关闭窗口后仍在托盘运行。配置与日志：`%APPDATA%\QMT Bridge\`。

开发模式：`pip install -e ".[full,desktop]"` 后执行 `qmt-desktop`。

### CLI（免环境二进制）

解压 `QMTBridge-CLI-*.zip` 后，与同目录 `runtime\` 一起使用（勿只拷贝单个 exe）。**配置以命令行参数为准**：

```text
qmt-server.exe --port 8000
qmt-server.exe --port 8000 --trading --api-key your-secret-key ^
  --mini-qmt-path "C:\你的QMT路径\userdata_mini" ^
  --stock-account-id 普通账户ID --credit-account-id 信用账户ID
qmt-server.exe --help
```

### pip / 源码

```bash
qmt-server --port 8080

qmt-server --port 8080 --trading --api-key your-secret-key \
  --mini-qmt-path "C:\你的QMT路径\userdata_mini" \
  --stock-account-id 普通账户ID --credit-account-id 信用账户ID
```

代码默认端口 **8000**；若 `.env` 里改了 `QMT_BRIDGE_PORT`，客户端必须用同一端口。验证：`http://127.0.0.1:<端口>/docs` 或 `GET /api/meta/health`。长期运行见 `scripts/pm2-start.bat`。

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
| [快速开始](docs/getting-started.md) | 安装、桌面包 / CLI、启动、客户端示例 |
| [REST API](docs/rest-api.md) | HTTP 参数与响应 |
| [WebSocket](docs/websocket.md) | 实时推送 |
| [Python 客户端](docs/api/index.md) | `QMTClient` |

## 许可

[MIT](LICENSE)
