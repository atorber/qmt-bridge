# 共享模块

| 文件 | 说明 |
|------|------|
| `common.py` | 环境、QMTClient、HTTP 错误处理 |
| `trading_fmt.py` | 买卖方向、委托状态、时间格式化 |
| `orders_util.py` | 委托表打印、按标的汇总 |
| `stock_names.py` | 批量股票中文名 |
| `kline_util.py` | 日 K 解析、多周期累计涨幅、形态条件概率 |

各 Skill 的 `scripts/*.py` 通过 `sys.path` 引用本目录（`parents[2]/_shared`）。

`qmt-bridge-trading/scripts/_common.py` 为兼容层，转发至 `common.py`。
