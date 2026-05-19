---
name: qmt-bridge-trading
description: >-
  通过 QMT Bridge HTTP API 执行证券交易：持仓/资产/委托查询、单笔与批量下单、撤单、清仓。
  在用户提到 qmt-bridge 交易、下单、持仓、清仓、撤单、查询资产，或需操作 miniQMT 账户时使用。
  本文件随 qmt-bridge 仓库发布于 skills/qmt-bridge-trading/SKILL.md。
---

# QMT Bridge 交易 Skill

> **发布位置**：`qmt-bridge` 仓库 `skills/qmt-bridge-trading/SKILL.md`。集成说明见同级 `skills/README.md` 与文档 [agent-skills.md](../../docs/agent-skills.md)。

通过已部署的 **QMT Bridge** 服务（FastAPI + miniQMT）完成真实交易操作。服务端须在 **Windows** 上运行，并启用交易模块。

## 可执行脚本（优先使用）

在仓库根目录执行（需 `pip install -e .`，环境变量见 `.env`）。**优先调用脚本**，避免在对话中手写长 curl/Python；脚本只输出摘要，不 dump 全量 JSON。

| 脚本 | 作用 | 示例 |
|------|------|------|
| `scripts/trading_status.py` | 只读：health + 账户状态 + 持仓/资产摘要 | `python skills/qmt-bridge-trading/scripts/trading_status.py` |
| `scripts/place_order.py` | 单笔下单（默认预览） | `.../place_order.py 000001.SZ --buy --volume 100 --execute --confirm` |
| `scripts/liquidate.py` | 清仓计划/执行（默认预览） | `.../liquidate.py` → 确认后 `.../liquidate.py --execute --confirm` |

路径均相对于本 skill 目录：`skills/qmt-bridge-trading/scripts/`。

**实盘提交**须同时带 `--execute --confirm`（`place_order` / `liquidate`）。交易前先跑 `trading_status.py`。

## 前置检查（每次交易前）

1. **服务可用**：`GET /api/meta/health`（无需 Key）
2. **交易已启用**：启动参数含 `--trading` 或 `QMT_BRIDGE_TRADING_ENABLED=true`
3. **认证**：所有 `/api/trading/*` 请求头携带 `X-API-Key: <密钥>`（与服务端 `QMT_BRIDGE_API_KEY` 一致）
4. **账户**：多账户时传 `account_id`；单账户可留空（使用服务端默认 `QMT_BRIDGE_TRADING_ACCOUNT_ID`）
5. **连接**：下单前建议 `GET /api/trading/account_status`，确认交易通道已连接

## 连接信息

从用户环境或项目 `.env` 读取（勿在对话中复述完整 API Key）：

| 变量 | 含义 |
|------|------|
| `QMT_BRIDGE_HOST` / 用户提供的 IP | 服务端地址 |
| `QMT_BRIDGE_PORT` | 端口，默认 `8000` |
| `QMT_BRIDGE_API_KEY` | 交易认证密钥 |
| `QMT_BRIDGE_TRADING_ACCOUNT_ID` | 默认资金账号（可选） |

**Python 客户端**（推荐，仓库已内置）：

```python
from qmt_bridge import QMTClient

client = QMTClient(host="192.168.1.100", port=8000, api_key="***")
```

**curl**：所有交易请求加 `-H "X-API-Key: $QMT_BRIDGE_API_KEY"`。

## 核心常量

| 字段 | 值 | 说明 |
|------|-----|------|
| `order_type` | `23` | 买入 |
| `order_type` | `24` | 卖出 |
| `price_type` | `5` | 最新价（默认） |
| `price_type` | `11` | 限价（须填 `price`） |
| `price_type` | `42` | 最优五档即时成交剩余撤销 |

**股票代码**：`代码.交易所`，如 `000001.SZ`、`600519.SH`。

**数量**：A 股通常为 100 的整数倍；卖出时使用 **`can_use_volume`（可用数量）**，勿超过持仓。

## 操作流程

### 1. 查询持仓

```bash
python skills/qmt-bridge-trading/scripts/trading_status.py
```

或 API / 客户端：

```python
resp = client.query_positions(account_id="")  # 可选 account_id
positions = resp.get("data", resp)
```

持仓记录常用字段：`stock_code`、`volume`（总持仓）、`can_use_volume`（可卖）、`open_price`、`market_value`。

**单标的持仓**：`GET /api/trading/position/{stock_code}` 或 `client.query_single_position("000001.SZ")`。

### 2. 查询资产与委托（辅助）

```python
asset = client.query_asset()           # 资金、市值等
orders = client.query_orders()         # 当日委托；cancelable_only=True 仅可撤
trades = client.query_trades()         # 当日成交
```

### 3. 单笔下单

**执行前必须向用户确认**：标的、方向、数量、价格类型与价格。

```bash
# 预览
python skills/qmt-bridge-trading/scripts/place_order.py 000001.SZ --buy --volume 100
# 提交
python skills/qmt-bridge-trading/scripts/place_order.py 000001.SZ --buy --volume 100 --execute --confirm
```

```python
result = client.place_order(
    stock_code="000001.SZ",
    order_type=23,           # 买入
    order_volume=100,
    price_type=5,            # 最新价
    price=0.0,
    strategy_name="",
    order_remark="agent",
    account_id="",
)
# 返回示例: {"order_id": <int>, "status": "submitted"}
```

```bash
curl -s -X POST "http://HOST:PORT/api/trading/order" \
  -H "Content-Type: application/json" -H "X-API-Key: KEY" \
  -d '{"stock_code":"000001.SZ","order_type":23,"order_volume":100,"price_type":5}'
```

限价示例：`price_type=11`, `price=10.50`。

### 4. 批量下单

请求体为 **OrderRequest 数组**（与单笔字段相同）。

```python
orders = [
    {"stock_code": "000001.SZ", "order_type": 23, "order_volume": 100, "price_type": 5},
    {"stock_code": "600519.SH", "order_type": 24, "order_volume": 100, "price_type": 5},
]
result = client.batch_order(orders)
# 返回: {"data": [{"stock_code": "...", "order_id": ...}, ...]}
```

```bash
curl -s -X POST "http://HOST:PORT/api/trading/batch_order" \
  -H "Content-Type: application/json" -H "X-API-Key: KEY" \
  -d '[{"stock_code":"000001.SZ","order_type":23,"order_volume":100}]'
```

批量接口在服务端 **顺序同步** 调用 `order()`，任一笔失败会中断后续（注意部分已成功的情况）。

### 5. 清仓（无独立 API）

清仓 = 对持仓中 **`can_use_volume > 0`** 的标的批量 **卖出**（`order_type=24`）。

```bash
python skills/qmt-bridge-trading/scripts/liquidate.py
python skills/qmt-bridge-trading/scripts/liquidate.py --codes 000001.SZ --execute --confirm
```

**标准流程**（未用脚本时）：

1. `query_positions()` 获取持仓列表
2. 过滤：`can_use_volume > 0`（可选：用户指定 `stock_codes` 子集）
3. **向用户展示待卖清单**（代码、可卖数量、市值），获得明确确认
4. 构造卖出委托列表，`price_type` 默认 `5`（最新价）；用户要求限价则 `11` + `price`
5. `batch_order(orders)` 或逐笔 `place_order`
6. 回报每笔 `order_id`；建议再查 `query_orders()` / `query_positions()` 核对

**清仓辅助逻辑（Python 片段，可在一次性脚本中使用）**：

```python
def build_liquidation_orders(positions, price_type=5, price=0.0, account_id="", remark="liquidate"):
    sell_type = 24
    items = positions if isinstance(positions, list) else []
    orders = []
    for p in items:
        vol = int(p.get("can_use_volume") or 0)
        code = p.get("stock_code") or p.get("stockCode")
        if not code or vol <= 0:
            continue
        orders.append({
            "stock_code": code,
            "order_type": sell_type,
            "order_volume": vol,
            "price_type": price_type,
            "price": price,
            "order_remark": remark,
            "account_id": account_id,
        })
    return orders

positions = client.query_positions().get("data", [])
orders = build_liquidation_orders(positions)
if orders:
    client.batch_order(orders)
```

**注意**：T+1 导致当日买入不可卖；科创板/创业板等可能有不同最小单位；停牌、涨跌停可能导致废单。

### 6. 撤单

```python
client.cancel_order(order_id=12345, account_id="")
# 批量: client.batch_cancel([{"order_id": 1}, {"order_id": 2}])
```

```bash
curl -s -X POST "http://HOST:PORT/api/trading/cancel" \
  -H "Content-Type: application/json" -H "X-API-Key: KEY" \
  -d '{"order_id":12345}'
```

## 安全与交互规范

1. **真实资金**：默认账户为实盘；未明确说明「模拟」时按实盘处理。
2. **双重确认**：下单、批量下单、清仓前必须列出参数并获得用户 **明确同意**（可参考 dashboard `6_交易管理.py` 的确认流程）。
3. **先查后动**：清仓/大额卖出前先 `query_positions` + `query_asset`。
4. **错误处理**：HTTP 401 → 检查 API Key；503 → QMT/xtdata 繁忙或锁超时；下单失败时记录错误信息，勿盲目重试同参数。
5. **日志**：用 `logging`，勿 `print` 敏感 Key。
6. **脚本**：使用本 skill 自带 `scripts/`，勿在仓库外留下一次性交易脚本。

## 响应结构约定

多数查询接口返回 `{"data": ...}`；下单返回 `{"order_id": ..., "status": "submitted"}`。客户端 `query_*` 可能直接返回外层 dict，用 `.get("data", resp)` 统一取列表/对象。

## 相关端点速查

| 操作 | 方法 | 路径 |
|------|------|------|
| 下单 | POST | `/api/trading/order` |
| 批量下单 | POST | `/api/trading/batch_order` |
| 撤单 | POST | `/api/trading/cancel` |
| 批量撤单 | POST | `/api/trading/batch_cancel` |
| 持仓 | GET | `/api/trading/positions` |
| 资产 | GET | `/api/trading/asset` |
| 委托 | GET | `/api/trading/orders` |
| 成交 | GET | `/api/trading/trades` |
| 账户状态 | GET | `/api/trading/account_status` |

完整列表见仓库 `docs/rest-api.md` 与 `src/qmt_bridge/client/trading.py`。

## 示例对话

**用户**：查一下当前持仓  
**Agent**：`query_positions` → 表格展示 `stock_code` / `volume` / `can_use_volume` / `market_value`

**用户**：限价 10.5 买入 000001.SZ 100 股  
**Agent**：确认参数 → `place_order(..., order_type=23, price_type=11, price=10.5)` → 返回 `order_id`

**用户**：全部清仓  
**Agent**：拉持仓 → 列出可卖标的与数量 → 用户确认 → `build_liquidation_orders` + `batch_order` → 汇总 `order_id` 并建议刷新持仓
