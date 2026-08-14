# API 自动化测试

## 1. 契约测试（默认，无需 QMT）

基于 **OpenAPI** + **mock xtquant**，在本地进程内验证全部 REST 路由。

```bash
pip install -e ".[server,test]"
python -m pytest tests/ -q
# 或 verbose
python -m pytest tests/ -v
```

| 文件 | 说明 |
|------|------|
| `conftest.py` | TestClient、mock 配置 |
| `mocks/` | xtdata / 交易管理器桩 |
| `openapi_harness.py` | 遍历 OpenAPI 构造请求 |
| `test_openapi_contract.py` | 全量 / 分 tag 契约测试 |

默认 `addopts` 会 **排除** `@pytest.mark.live` 联调用例。

---

## 2. 联调测试（真实 Bridge，如 `8080`）

对已启动的 **QMT Bridge** 发真实 HTTP 请求（Windows 上 QMT + `qmt-server` 需先运行）。

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `QMT_BRIDGE_LIVE` | _(未设置)_ | 设为 `1` 才执行联调，否则整组 skip |
| `QMT_BRIDGE_HOST` | `127.0.0.1` | 服务地址 |
| `QMT_BRIDGE_PORT` | `8080` | 服务端口 |
| `QMT_BRIDGE_LIVE_URL` | — | 完整 URL，设置后覆盖 host/port |
| `QMT_BRIDGE_API_KEY` | — | 交易类接口必填（与服务端一致） |
| `QMT_BRIDGE_LIVE_TIMEOUT` | `30` | 单请求超时（秒） |
| `QMT_BRIDGE_LIVE_FULL` | — | 设为 `1` 启用全量 OpenAPI 扫端 |
| `QMT_BRIDGE_LIVE_MAX_FAILURES` | `0` | 全量扫端允许失败数 |

### 运行

```bash
# PowerShell
$env:QMT_BRIDGE_LIVE = "1"
$env:QMT_BRIDGE_PORT = "8080"
$env:QMT_BRIDGE_API_KEY = "your-secret-key"   # 若已启用交易
QMT_BRIDGE_LIVE=1 QMT_BRIDGE_PORT=8080 python -m pytest tests/live -m live -v
```

### 用例说明

| 文件 | 内容 |
|------|------|
| `live/test_smoke.py` | 健康检查、板块、快照、交易日历 |
| `live/test_trading_live.py` | 持仓/资产/委托（无交易模块或 Key 时 skip） |
| `live/test_openapi_live.py` | 只读 OpenAPI 扫端；`LIVE_FULL=1` 时全量扫端 |

服务不可达时联调用例会自动 **skip**，不会导致 CI 失败。
