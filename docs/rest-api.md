# REST API 端点速查

!!! tip "交互式文档"
    服务运行后，访问 `http://<host>:8080/docs`（Swagger UI）或 `http://<host>:8080/redoc`（ReDoc）可在线查看并测试。本文与路由实现（`src/qmt_bridge/server/routers/`、`models.py`）对齐。

## 约定

| 项 | 说明 |
|----|------|
| 代码格式 | 如 `000001.SZ`、`600519.SH`、`000300.SH` |
| 时间格式 | `YYYYMMDD` 或 `YYYYMMDDHHmmss`；空字符串表示不限制 |
| 多代码 Query | 逗号分隔：`stocks=000001.SZ,600519.SH` |
| JSON 列表字段 | `stock_list` 与别名 `stocks` 均可（`populate_by_name`） |
| K 线周期 `period` | `tick` / `1m` / `5m` / `15m` / `30m` / `60m` / `1d` |
| 除权 `dividend_type` | `none` / `front` / `back` / `front_ratio` / `back_ratio` |
| 认证 | 交易/信用/资金/SMT/银证：请求头 `X-API-Key`；服务需 `--trading` |
| 账户 | `account_id` 空则用服务端默认账户；`account_type` 为 `STOCK` 或 `CREDIT` |

**响应包装**（按端点不同）：

- 多数查询：`{"data": ...}`，或带业务键如 `{"stock", "data"}` / `{"sectors"}`
- 写操作常见：`{"status": "ok", "data": ...}`
- `ok_response()`：`{"code": 0, "message": "ok", "data": ...}`
- `data` 多为 xtquant 序列化结果（对象属性展开为 dict/list），字段随 QMT 版本变化

**HTTP 错误**：参数校验失败 `422`；交易认证失败 `401`/`403`；部分行情超时 `504`、底层失败 `502`、锁等待超时 `503`。

---

## Legacy 端点（向后兼容）

建议改用对应新路径。GET 用 Query；`POST /api/download` 用 JSON Body。

### `GET /api/history`

单只历史 K 线。替代：`/api/market/market_data` 或 `/api/market/market_data_ex`。

| 参数 | 位置 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|------|
| stock | Query | string | 是 | | 如 `000001.SZ` |
| period | Query | string | 否 | `1d` | K 线周期 |
| count | Query | int | 否 | `100` | 条数 |
| fields | Query | string | 否 | `open,high,low,close,volume` | 逗号分隔字段 |

**响应**

```json
{"stock": "000001.SZ", "period": "1d", "count": 100, "data": [{"time": "...", "open": 10.1, "high": 10.2, "low": 10.0, "close": 10.15, "volume": 12345}]}
```

### `GET /api/batch_history`

| 参数 | 位置 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|------|
| stocks | Query | string | 是 | | 逗号分隔代码 |
| period | Query | string | 否 | `1d` | |
| count | Query | int | 否 | `100` | |
| fields | Query | string | 否 | `open,high,low,close,volume` | |

**响应**：`{"stocks": [...], "period": "...", "count": 100, "data": {"000001.SZ": [记录...]}}`

### `GET /api/full_tick`

| 参数 | 位置 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| stocks | Query | string | 是 | 逗号分隔 |

**响应**：`{"data": {"000001.SZ": {快照字段...}}}`

### `GET /api/sector_stocks`

| 参数 | 位置 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| sector | Query | string | 是 | 板块名，如 `沪深A股` |

**响应**：`{"sector": "沪深A股", "stocks": ["000001.SZ", ...]}`

### `GET /api/instrument_detail`

| 参数 | 位置 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| stock | Query | string | 是 | |

**响应**：`{"stock": "...", "detail": {...}}`

### `POST /api/download`

JSON Body：

| 字段 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| stock | string | 是 | | |
| period | string | 否 | `1d` | |
| start | string | 否 | `""` | 开始时间 |
| end | string | 否 | `""` | 结束时间 |

**响应**：`{"status": <下载状态>, "stock": "...", "period": "1d"}`

---

## Market — 行情 `/api/market/*`

### `GET /api/market/full_tick`

| 参数 | 位置 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| stocks | Query | string | 是 | 逗号分隔，个股/指数 |

**响应**：`{"data": {代码: 快照}}`。快照常见字段含最新价、涨跌、买卖盘等（随 xtquant）。

### `GET /api/market/indices`

无参数。固定查询：上证、深成、创业板、沪深300、上证50、中证500、中证1000。

**响应**：`{"indices": ["000001.SH", ...], "data": {代码: 快照}}`

### `GET /api/market/market_data_ex`

增强 K 线（推荐）。

| 参数 | 位置 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|------|
| stocks | Query | string | 是 | | 逗号分隔 |
| period | Query | string | 否 | `1d` | |
| start_time | Query | string | 否 | `""` | |
| end_time | Query | string | 否 | `""` | |
| count | Query | int | 否 | `-1` | `-1` 不限 |
| dividend_type | Query | string | 否 | `none` | |
| fill_data | Query | bool | 否 | `true` | 填充空档 |

**响应**：`{"data": {"000001.SZ": [{"time": "...", "open": ..., "high": ..., "low": ..., "close": ..., "volume": ...}, ...]}}`

### `GET /api/market/local_data`

参数同 `market_data_ex`。只读本地缓存，不向行情服务器补数。

**响应**：同 `market_data_ex`。

### `GET /api/market/divid_factors`

| 参数 | 位置 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|------|
| stock | Query | string | 是 | | 单只 |
| start_time | Query | string | 否 | `""` | |
| end_time | Query | string | 否 | `""` | |
| timeout_sec | Query | float | 否 | 服务端默认 | `0.5~120`，覆盖 `QMT_BRIDGE_DIVID_FACTORS_TIMEOUT_SEC`（默认 8s） |

**响应**：`{"stock": "...", "data": [...]}`

**错误**：超时 `504`；底层异常/无数据 `502`；xtdata 锁等待超时 `503`（`QMT_BRIDGE_XTDATA_LOCK_WAIT_TIMEOUT_SEC`，默认 15s）。

### `GET /api/market/market_data`

原始 `get_market_data`，按字段组织后转为记录。

| 参数 | 位置 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|------|
| stocks | Query | string | 是 | | |
| fields | Query | string | 否 | `open,high,low,close,volume` | 逗号分隔 |
| period | Query | string | 否 | `1d` | |
| start_time / end_time | Query | string | 否 | `""` | |
| count | Query | int | 否 | `-1` | |
| dividend_type | Query | string | 否 | `none` | |
| fill_data | Query | bool | 否 | `true` | |
| timeout_sec | Query | float | 否 | 服务端默认 | `0.5~180` |

**响应**：`{"data": {"000001.SZ": [记录...]}}`。超时/失败同 divid_factors（`504`/`502`）。

### `GET /api/market/market_data3`

参数同 `market_data`，但 `fields` 默认空（取全部字段），无 `timeout_sec`。

**响应**：`{"data": {代码: [记录...]}}`

### `GET /api/market/full_kline`

| 参数 | 位置 | 类型 | 必填 | 默认 |
|------|------|------|------|------|
| stock | Query | string | 是 | |
| period | Query | string | 否 | `1d` |
| start_time / end_time | Query | string | 否 | `""` |

**响应**：`{"stock": "...", "data": ...}`

### `GET /api/market/fullspeed_orderbook`

| 参数 | 位置 | 类型 | 必填 |
|------|------|------|------|
| stock | Query | string | 是 |
| start_time / end_time | Query | string | 否 |

**响应**：`{"stock": "...", "data": ...}`（极速委托簿，需对应行情权限）

### `GET /api/market/transactioncount`

参数同 `fullspeed_orderbook`。

**响应**：`{"stock": "...", "data": ...}`

---

## Tick & L2 — `/api/tick/*`

L2 / 千档需对应行情权限。下列接口除特别说明外，Query 均为：

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| stock | string | 是 | | |
| start_time | string | 否 | `""` | |
| end_time | string | 否 | `""` | |
| count | int | 否 | `-1` | `-1` 不限 |

**响应（带时间范围的接口）**：`{"stock": "...", "data": ...}`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/tick/l2_quote` | L2 报价（含 start/end/count） |
| GET | `/api/tick/l2_order` | L2 逐笔委托 |
| GET | `/api/tick/l2_transaction` | L2 逐笔成交 |
| GET | `/api/tick/l2_thousand_quote` | 千档报价 |
| GET | `/api/tick/l2_thousand_orderbook` | 千档委托簿 |
| GET | `/api/tick/l2_thousand_trade` | 千档成交 |

仅 `stock`：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/tick/l2_thousand_queue` | 千档委托队列 |
| GET | `/api/tick/broker_queue` | 经纪商队列 |
| GET | `/api/tick/order_rank` | 委托排名 |

---

## Sector — `/api/sector/*`

JSON 中 `stocks` 与 `stock_list` 等价。

### `GET /api/sector/list`

无参数。**响应**：`{"sectors": ["沪深A股", ...]}`

### `GET /api/sector/stocks`

| 参数 | 位置 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|------|
| sector | Query | string | 是 | | 如 `沪深A股` |
| real_timetag | Query | int | 否 | `-1` | 历史毫秒时间戳，`-1` 最新 |

**响应**：`{"sector": "...", "count": 123, "stocks": ["000001.SZ", ...]}`

### `GET /api/sector/info`

| 参数 | 位置 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|------|
| sector | Query | string | 否 | `""` | 空则全部；不存在时 `{"data": {}}` |

### `POST /api/sector/create_folder`

Body：`{"folder_name": "我的板块"}`  
**响应**：`{"status": "ok", "data": ...}`

### `POST /api/sector/create`

Body：`{"sector_name": "自选", "parent_node": ""}`（`parent_node` 默认空）

### `POST /api/sector/add_stocks` / `remove_stocks` / `reset`

Body：`{"sector_name": "自选", "stocks": ["000001.SZ"]}`  
`reset` 用新列表**整体替换**成分股。

### `DELETE /api/sector/remove`

| 参数 | 位置 | 类型 | 必填 |
|------|------|------|------|
| sector_name | Query | string | 是 |

---

## Calendar — `/api/calendar/*`

市场代码：`SH` / `SZ` / `IF` / `DF` / `SF` / `ZF` 等。

### `GET /api/calendar/trading_dates`

| 参数 | 位置 | 类型 | 必填 | 默认 |
|------|------|------|------|------|
| market | Query | string | 是 | |
| start_time / end_time | Query | string | 否 | `""` |
| count | Query | int | 否 | `-1` |

**响应**：`{"market": "SH", "dates": [时间戳或日期, ...]}`

### `GET /api/calendar/holidays`

无参数。**响应**：`{"holidays": [...]}`

### `GET /api/calendar/trading_calendar`

| 参数 | 必填 |
|------|------|
| market | 是 |
| start_time / end_time | 否 |

**响应**：`{"market": "...", "calendar": ...}`

### `GET /api/calendar/trading_period`

| 参数 | 必填 | 说明 |
|------|------|------|
| stock | 是 | 合约代码 |

**响应**：`{"stock": "...", "periods": ...}`（如 9:30–11:30、13:00–15:00）

### `GET /api/calendar/is_trading_date`

| 参数 | 必填 | 说明 |
|------|------|------|
| market | 是 | |
| date | 是 | `YYYYMMDD` |

**响应**：`{"market": "SH", "date": "20260105", "is_trading": true}`

### `GET /api/calendar/prev_trading_date` / `next_trading_date`

| 参数 | 必填 | 默认 | 说明 |
|------|------|------|------|
| market | 是 | | |
| date | 否 | `""`（今天） | 参考日 |

**响应**：`{"market": "...", "prev_trading_date": ...}` 或 `next_trading_date`；不足时可能为 `null`。

### `GET /api/calendar/trading_dates_count`

| 参数 | 必填 |
|------|------|
| market | 是 |
| start_time / end_time | 否 |

**响应**：`{"market": "...", "count": 242}`

---

## Financial — `/api/financial/*`

### `GET /api/financial/data` 与 `GET /api/financial/data_ori`

| 参数 | 位置 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|------|
| stocks | Query | string | 是 | | 逗号分隔 |
| tables | Query | string | 否 | `""` | 空=全部。常用：`Balance`、`Income`、`CashFlow` |
| start_time / end_time | Query | string | 否 | `""` | |
| report_type | Query | string | 否 | `report_time` | `report_time` / `announce_time` |

**响应**：`{"data": ...}`。`data` 为按股票/表整理的记录；`data_ori` 为原始结构序列化。

---

## Instrument — `/api/instrument/*`

### `GET /api/instrument/detail_list`

| 参数 | 必填 | 默认 | 说明 |
|------|------|------|------|
| stocks | 是 | | 逗号分隔 |
| iscomplete | 否 | `false` | `true` 返回完整字段 |

**响应**：`{"data": {代码: 详情}}`

### `GET /api/instrument/type`

| 参数 | 必填 |
|------|------|
| stock | 是 |

**响应**：`{"stock": "...", "type": "stock"}`（如 stock / index / fund）

### `GET /api/instrument/ipo_info`

| 参数 | 必填 |
|------|------|
| start_time / end_time | 否 |

**响应**：`{"data": [...]}`

### `GET /api/instrument/index_weight`

| 参数 | 必填 | 说明 |
|------|------|------|
| index_code | 是 | 如 `000300.SH` |

**响应**：`{"index_code": "...", "data": ...}`

### `GET /api/instrument/his_st_data`

| 参数 | 必填 |
|------|------|
| stock | 是 |

**响应**：`{"stock": "...", "data": ...}`

---

## Option — `/api/option/*`

### `GET /api/option/detail`

| 参数 | 必填 |
|------|------|
| option_code | 是 |

**响应**：`{"option_code": "...", "data": ...}`（行权价、到期日、乘数等）

### `GET /api/option/chain`

| 参数 | 必填 | 说明 |
|------|------|------|
| undl_code | 是 | 标的，如 `000300.SH` |

**响应**：`{"undl_code": "...", "data": ...}`

### `GET /api/option/list`

| 参数 | 必填 | 默认 | 说明 |
|------|------|------|------|
| undl_code | 是 | | |
| dedate | 是 | | 到期日 |
| opttype | 否 | `""` | 认购/认沽，空不筛 |
| isavailable | 否 | `false` | 仅可交易 |

**响应**：`{"data": ...}`

### `GET /api/option/his_option_list`

| 参数 | 必填 | 说明 |
|------|------|------|
| undl_code | 是 | |
| dedate | 是 | 历史日期 |

**响应**：`{"data": ...}`

---

## ETF `/api/etf/*`

### `GET /api/etf/list`

无参数。**响应**：`{"count": N, "stocks": ["510300.SH", ...]}`

### `GET /api/etf/info`

| 参数 | 必填 | 说明 |
|------|------|------|
| stock | 是 | 如 `510300.SH` |

**成功响应**

```json
{
  "stock": "510300.SH",
  "name": "...",
  "nav": 0,
  "component_count": 300,
  "components": [{"stock_code": "600519.SH", "volume": 100}],
  "raw": {}
}
```

未找到：`{"stock": "...", "error": "未找到该 ETF 信息"}`

---

## CB — `/api/cb/*`

### `GET /api/cb/list`

无参数。**响应**：`{"count": N, "stocks": [...]}`

### `GET /api/cb/info`

| 参数 | 必填 |
|------|------|
| stock | 是 |

**响应**：`{"stock": "...", "data": ...}`（转股价、到期日等）

---

## Futures — `/api/futures/*`

### `GET /api/futures/main_contract` / `sec_main_contract`

| 参数 | 必填 | 说明 |
|------|------|------|
| code_market | 是 | 品种，如 `IF.CFE` |
| start_time / end_time | 否 | |

**响应**：`{"code_market": "IF.CFE", "data": ...}`

查询前通常需先 `POST /api/download/metatable_data`。

---

## Formula — `/api/formula/*`

### `POST /api/formula/call`

Body：

| 字段 | 类型 | 必填 | 默认 |
|------|------|------|------|
| formula_name | string | 是 | |
| stock_code | string | 是 | |
| period | string | 否 | `1d` |
| start_time / end_time | string | 否 | `""` |
| count | int | 否 | `-1` |
| dividend_type | string | 否 | `none` |
| params | object | 否 | `{}` | 额外关键字参数 |

**响应**：`{"data": ...}`

### `POST /api/formula/call_batch`

同 `call`，但 `stock_codes: string[]` 必填（替代 `stock_code`）。

### `POST /api/formula/generate_index_data`

| 字段 | 类型 | 必填 | 默认 |
|------|------|------|------|
| index_code | string | 是 | |
| stocks / stock_list | string[] | 否 | `[]` |
| weights | float[] | 是 | |
| period | string | 否 | `1d` |
| start_time / end_time | string | 否 | `""` |

**响应**：`{"data": ...}`

### `POST /api/formula/create`

Body：`{"formula_name": "...", "formula_file": "...", "formula_type": ""}`  
**响应**：`{"code": 0, "message": "ok", "data": ...}`

### `POST /api/formula/import`

Body：`{"formula_file": "..."}` → `ok_response`

### `DELETE /api/formula/delete`

Query：`formula_name` 必填 → `ok_response`

### `GET /api/formula/list`

无参数 → `ok_response`（公式列表）

---

## HK — `/api/hk/*`

### `GET /api/hk/stock_list`

无参数。沪港通 + 深港通。**响应**：`{"count": N, "stocks": [...]}`

### `GET /api/hk/connect_stocks`

| 参数 | 必填 | 默认 | 说明 |
|------|------|------|------|
| connect_type | 否 | `north` | `north`：沪股通+深股通；`south`：港股通 |

**响应**：`{"connect_type": "north", "count": N, "stocks": [...]}`

### `GET /api/hk/broker_dict`

无参数。**响应**：`{"data": ...}`

---

## Tabular — `/api/tabular/*`

### `GET /api/tabular/data` / `formula`

| 参数 | 必填 | 默认 | 说明 |
|------|------|------|------|
| table_name | 是 | | 表名 |
| stocks | 否 | `""` | 逗号分隔，空=全部 |
| start_time / end_time | 否 | `""` | |

**响应**：`{"table": "...", "data": ...}`

### `GET /api/tabular/tables`

无参数。**响应**：`{"tables": [...]}`；接口不可用时 `[]`。

---

## Utility — `/api/utility/*`

### `GET /api/utility/stock_name`

| 参数 | 必填 |
|------|------|
| stock | 是 |

**响应**：`{"stock": "000001.SZ", "name": "平安银行"}`

### `GET /api/utility/batch_stock_name`

| 参数 | 必填 |
|------|------|
| stocks | 是 | 逗号分隔 |

**响应**：`{"data": {"000001.SZ": "平安银行"}}`

### `GET /api/utility/code_to_market`

| 参数 | 必填 |
|------|------|
| stock | 是 |

**响应**：`{"stock": "...", "market": "SZ", "type": "..."}`（`market` 取代码后缀）

### `GET /api/utility/search`

| 参数 | 必填 | 默认 | 说明 |
|------|------|------|------|
| keyword | 是 | | 代码或中文名 |
| category | 否 | `沪深A股` | 搜索板块 |
| limit | 否 | `20` | |

中文关键字会构建名称缓存（首次较慢）。**响应**：`{"keyword": "...", "count": N, "stocks": [...]}`

---

## Meta — `/api/meta/*`

| 方法 | 路径 | 参数 | 响应 |
|------|------|------|------|
| GET | `/health` | 无 | `{"status": "ok"}`；`--trading` 时另有 `trading: {enabled, connected, error}` |
| GET | `/version` | 无 | `{"version": "x.y.z"}` |
| GET | `/xtdata_version` | 无 | `{"xtdata_version": "..."}` 或 `"unknown"` |
| GET | `/connection_status` | 无 | `{"connected": true}` 或 `{"connected": false, "error": "..."}` |
| GET | `/markets` | 无 | `{"markets": [...]}` |
| GET | `/period_list` | 无 | `{"periods": ["tick", "1m", ...]}` |
| GET | `/stock_list` | Query `category` **必填**（如 `沪深A股`） | `{"category": "...", "count": N, "stocks": [...]}` |
| GET | `/last_trade_date` | Query `market` **必填** | `{"market": "SH", "last_trade_date": ...}` |
| GET | `/quote_server_status` | 无 | `{"data": ...}` 或 `{"error": "..."}` |

`/api/meta/health` **无需** API Key。

---

## Download — `/api/download/*`

均为 POST。无 Body 的接口响应多为 `{"status": "ok"}`。带 `stocks`/`tables` 别名。

### `POST /api/download/history_data2`

Body：`{"stocks": ["000001.SZ"], "period": "1d", "start_time": "20230101", "end_time": ""}`  
`period` 默认 `1d`。后台下载，进度见 WebSocket `/ws/download_progress`。

**响应**：`{"status": "ok", "stocks": [...], "period": "1d", "result": ...}`

### `POST /api/download/financial_data`

Body：`{"stocks": [...], "tables": ["Balance", "Income"], "start_time": "", "end_time": ""}`  
异步后台。**响应**：`{"status": "ok", "stocks": [...], "tables": [...]}`

### `POST /api/download/financial_data2`

Body：`{"stocks": [...], "tables": [...]}`（无时间范围）。**同步阻塞**。响应同上。

### 无 Body（多为启动时自动预下载，每 24h 刷新）

| 路径 | 说明 |
|------|------|
| `/sector_data` | 板块成分 |
| `/index_weight` | 指数权重 |
| `/etf_info` | ETF 申赎 |
| `/cb_data` | 可转债 |
| `/history_contracts` | 过期合约 |
| `/metatable_data` | 合约元数据（查期货前建议调用） |
| `/holiday_data` | 节假日 |

### `POST /api/download/his_st_data`

Body：`{"stocks": [...], "period": "1d", "start_time": "", "end_time": ""}`  
**响应**：`{"status": "ok", "stocks": [...], "result": ...}`

### `POST /api/download/tabular_data`

Body：`{"tables": ["表名"]}`  
**响应**：`{"status": "ok", "tables": [...], "result": ...}`

---

## Trading — `/api/trading/*` :material-lock:

请求头：`X-API-Key`。`order_type` / `price_type` 对齐 xtquant 常量（如限价、市价等）。

### `POST /api/trading/order`

Body：

| 字段 | 类型 | 必填 | 默认 |
|------|------|------|------|
| stock_code | string | 是 | |
| order_type | int | 是 | |
| order_volume | int | 是 | |
| price_type | int | 否 | `5` |
| price | float | 否 | `0.0` |
| account_id | string | 否 | `""` |
| strategy_name | string | 否 | `""` |
| order_remark | string | 否 | `""` |

**响应**：`{"order_id": <委托号>, "status": "submitted"}`

### `POST /api/trading/order_async`

Body 字段同 `order`。**响应**：`{"seq": <异步序号>, "status": "async_submitted"}`

### `POST /api/trading/cancel`

Body：`{"order_id": 123, "account_id": ""}`  
**响应**：`{"status": "ok", "data": ...}`

### `POST /api/trading/cancel_async`

Body 同 `cancel`。**响应**：`{"seq": ..., "status": "async_submitted"}`

### `POST /api/trading/cancel_by_sysid` / `cancel_by_sysid_async`

Body：`{"market": "SZ", "sysid": "...", "account_id": ""}`  
**响应**：`ok_response`

### `POST /api/trading/batch_order`

Body：`OrderRequest` **数组**。任一笔失败会中断后续（前面可能已成功）。

**响应**：`{"data": [{"stock_code": "...", "order_id": ...}, ...]}`

### `POST /api/trading/batch_cancel`

Body：`CancelRequest` 数组。**响应**：`{"data": [{"order_id": ..., "result": ...}, ...]}`

### 查询类（Query）

公共可选 Query：`account_id`（默认 `""`）、多数还有 `account_type`（`STOCK`/`CREDIT`，默认 `""`）。

| 方法 | 路径 | 额外 Query | 响应 |
|------|------|------------|------|
| GET | `/orders` | `cancelable_only` bool 默认 `false` | `{"data": [委托...]}` |
| GET | `/trades` | | `{"data": [成交...]}` |
| GET | `/history_trades` | `start_time` 必填、`end_time` 可选，`YYYYMMDD` | `{"data": [历史成交...]}`；底层 `export_data`+`query_data`（`deal`） |
| GET | `/history_orders` | 同上 | `{"data": [历史委托...]}`；`data_type=order`，部分券商无数据 |
| GET | `/positions` | | `{"data": [持仓...]}` |
| GET | `/asset` | | `{"data": {资产...}}` |
| GET | `/order_detail` | `order_id` int 默认 `0` | `{"data": ...}` |
| GET | `/order/{order_id}` | Path `order_id` | `{"data": ...}` |
| GET | `/trade/{trade_id}` | Path `trade_id` | `{"data": ...}` |
| GET | `/position/{stock_code}` | Path 代码 | `{"data": ...}` |
| GET | `/account_status` | `account_id` | `{"data": ...}` |
| GET | `/account_status_detail` | 无 | `ok_response` |
| GET | `/account_infos` | 无 | `{"data": ...}` |
| GET | `/secu_account` | `account_id` | `ok_response` |
| GET | `/new_purchase_limit` | `account_id` | `{"data": ...}` |
| GET | `/ipo_data` | 无 | `{"data": ...}` |
| GET | `/com_fund` | `account_id` | `{"data": ...}` 期权/期货资金 |
| GET | `/com_position` | `account_id` | `{"data": ...}` |

### `POST /api/trading/export_data` / `query_data`

Body：

| 字段 | 类型 | 必填 | 默认 |
|------|------|------|------|
| result_path | string | 是 | |
| data_type | string | 是 | |
| start_time / end_time | string | 否 | `""` |
| user_param | string | 否 | `""` |
| account_id | string | 否 | `""` |

**响应**：`ok_response`

### `POST /api/trading/sync_transaction`

Body：`{"operation": "...", "data_type": "...", "deal_list": [{}], "account_id": ""}`  
**响应**：`ok_response`

---

## Credit — `/api/credit/*` :material-lock:

### `POST /api/credit/order`

Body 同普通 `OrderRequest`（`CreditOrderRequest`）：`stock_code`、`order_type`、`order_volume` 必填；`price_type` 默认 5。`order_type` 区分融资买入/融券卖出等。

**响应**：`{"order_id": ..., "status": "submitted"}`

### 查询

可选 Query：`account_id`；持仓/资产/负债另有 `account_type` 默认 `CREDIT`。

| 方法 | 路径 | 别名 | 响应 |
|------|------|------|------|
| GET | `/positions` | | `{"data": ...}` |
| GET | `/positions/breakdown` | | `{"data": ...}` 总=融资+担保品 |
| GET | `/asset` | `/detail` | `{"data": ...}`；xtquant 返回 None 时 `503` |
| GET | `/debt` | `/stk_compacts` | `{"data": ...}` |
| GET | `/slo_stocks` | `/slo_code` | `{"data": ...}` 可融券 |
| GET | `/subjects` | | `{"data": ...}` |
| GET | `/assure` | | `{"data": ...}` |

---

## Fund — `/api/fund/*` :material-lock:

响应均为 `ok_response`。

### `POST /api/fund/transfer`

Body：`{"transfer_direction": 0, "amount": 1000.0, "account_id": ""}`（`transfer_direction`、`amount` 必填）

### `POST /api/fund/ctp_option_to_future` / `ctp_future_to_option`

Body：`{"opt_account_id": "...", "ft_account_id": "...", "balance": 1000.0}` 均必填。

### `POST /api/fund/secu_transfer`

| 字段 | 类型 | 必填 |
|------|------|------|
| transfer_direction | int | 是 |
| stock_code | string | 是 |
| volume | int | 是 |
| transfer_type | int | 是 |
| account_id | string | 否 |

---

## SMT — `/api/smt/*` :material-lock:

查询 GET，可选 Query `account_id`。响应 `ok_response`。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/quoter` | 报价方 |
| GET | `/compact` | 合约 |
| GET | `/orders` | 委托 |

### `POST /api/smt/negotiate_order_async`

| 字段 | 类型 | 必填 | 默认 |
|------|------|------|------|
| src_group_id | string | 是 | |
| order_code | string | 是 | |
| date | string | 是 | |
| amount | float | 是 | |
| apply_rate | float | 是 | |
| dict_param | object | 否 | `{}` |
| account_id | string | 否 | `""` |

### `POST /api/smt/appointment_order_async`

`order_code`、`date`、`amount`、`apply_rate` 必填；`account_id` 可选。

### `POST /api/smt/appointment_cancel_async`

`apply_id` 必填；`account_id` 可选。

### `POST /api/smt/compact_renewal_async`

`cash_compact_id`、`order_code`、`defer_days`、`defer_num`、`apply_rate` 必填。

### `POST /api/smt/compact_return_async`

`src_group_id`、`cash_compact_id`、`order_code`、`occur_amount` 必填。

---

## Bank — `/api/bank/*` :material-lock:

除查询流水为 GET 外，转账/余额为 POST（含密码）。响应 `ok_response`。

### `POST /api/bank/transfer_in` / `transfer_out` / `transfer_in_async` / `transfer_out_async`

| 字段 | 类型 | 必填 | 默认 |
|------|------|------|------|
| bank_no | string | 是 | |
| bank_account | string | 是 | |
| balance | float | 是 | |
| bank_pwd | string | 否 | `""` |
| fund_pwd | string | 否 | `""` |
| account_id | string | 否 | `""` |

### `GET /api/bank/info`

Query：`account_id` 可选。

### `POST /api/bank/amount`

Body：`{"bank_no": "...", "bank_account": "...", "bank_pwd": "...", "account_id": ""}`（前三项必填）

### `GET /api/bank/transfer_stream`

| 参数 | 位置 | 必填 | 默认 |
|------|------|------|------|
| start_date / end_date | Query | 是 | |
| bank_no / bank_account / account_id | Query | 否 | `""` |
