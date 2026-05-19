# Agent Skills



本目录包含与 **QMT Bridge** 配套的 [Agent Skills](https://docs.cursor.com/context/skills)。**19 个 Skill** 均已提供可执行脚本（见 [ROADMAP.md](ROADMAP.md)）。



## 全部 Skills



| Skill | 说明 | just 示例 |

|-------|------|-----------|

| [qmt-bridge-trading](qmt-bridge-trading/SKILL.md) | 下单、清仓、状态 | `just agent-trading-status` |

| [qmt-bridge-execution-review](qmt-bridge-execution-review/SKILL.md) | 当日复盘 | `just agent-daily-report` |

| [qmt-bridge-portfolio-risk](qmt-bridge-portfolio-risk/SKILL.md) | 组合风险 | `just agent-portfolio-risk` |

| [qmt-bridge-daily-pnl](qmt-bridge-daily-pnl/SKILL.md) | 当日盈亏 | `just agent-daily-pnl` |

| [qmt-bridge-order-ops](qmt-bridge-order-ops/SKILL.md) | 查单、撤单 | `just agent-list-orders` |

| [qmt-bridge-market-watch](qmt-bridge-market-watch/SKILL.md) | 自选快照 | `just agent-watchlist --codes ...` |

| [qmt-bridge-sector-theme](qmt-bridge-sector-theme/SKILL.md) | 板块排序 | `just agent-sector-rank --sector 沪深A股` |

| [qmt-bridge-financial-download](qmt-bridge-financial-download/SKILL.md) | 下载财报 | `just agent-download-financial --codes ... --verify` |

| [qmt-bridge-fundamental-screen](qmt-bridge-fundamental-screen/SKILL.md) | 财报筛选 | `just agent-screen-financial --codes ...` |

| [qmt-bridge-technical-signal](qmt-bridge-technical-signal/SKILL.md) | 公式检查 | `just agent-formula-check --list` |

| [qmt-bridge-smart-execution](qmt-bridge-smart-execution/SKILL.md) | 下单预览 | `just agent-execution-preview ...` |

| [qmt-bridge-rebalance](qmt-bridge-rebalance/SKILL.md) | 再平衡 | `just agent-rebalance --targets '...'` |

| [qmt-bridge-credit-margin](qmt-bridge-credit-margin/SKILL.md) | 两融快照 | `just agent-credit-snapshot` |

| [qmt-bridge-realtime-monitor](qmt-bridge-realtime-monitor/SKILL.md) | WS 示例 | `just agent-ws-subscribe --codes ...` |

| [qmt-bridge-event-calendar](qmt-bridge-event-calendar/SKILL.md) | 交易日历 | `just agent-calendar` |

| [qmt-bridge-etf](qmt-bridge-etf/SKILL.md) | ETF | `just agent-etf-snapshot --list` |

| [qmt-bridge-convertible](qmt-bridge-convertible/SKILL.md) | 可转债 | `just agent-cb-snapshot --list` |

| [qmt-bridge-option](qmt-bridge-option/SKILL.md) | 期权链 | `just agent-option-chain --undl 510050.SH` |

| [qmt-bridge-hk-connect](qmt-bridge-hk-connect/SKILL.md) | 港股通 | `just agent-hk-universe` |



## 推荐工作流



```

calendar → watchlist / sector-rank

    → download-financial → fundamental-screen

    → portfolio-risk → daily-pnl → execution-preview → trading → order-ops → daily-report

```



## 运行方式



### 使用 just（本机已安装 just 时）



```bash

just agent-trading-status --port 8080 --api-key YOUR_KEY

```



### 无 just 时（Agent 终端常用）



在仓库根目录直接调用 Python：



```bash

python skills/qmt-bridge-trading/scripts/trading_status.py --host 127.0.0.1 --port 8080 --api-key YOUR_KEY

```



### 连接与编码



- **端口**：以 `.env` 中 `QMT_BRIDGE_HOST` / `QMT_BRIDGE_PORT` 为准（默认端口 8000；若你使用 8080 请显式传入 `--port 8080`）

- **Windows 中文乱码**：PowerShell 可先执行 `chcp 65001`，或设置 `PYTHONIOENCODING=utf-8`



## 共享模块



[`_shared/common.py`](_shared/common.py) · [`financial_util.py`](_shared/financial_util.py) · [`positions_util.py`](_shared/positions_util.py) · [`stock_names.py`](_shared/stock_names.py) · [`trading_fmt.py`](_shared/trading_fmt.py) · [`orders_util.py`](_shared/orders_util.py)



## Cursor 启用



```bash

mkdir -p .cursor/skills

for d in skills/qmt-bridge-*/; do

  name=$(basename "$d")

  ln -sf "../../skills/$name" ".cursor/skills/$name"

done

```



## 前置条件



- Bridge 已启动；交易脚本需 `QMT_BRIDGE_API_KEY` 与 Bridge 侧 `--trading`

- 写操作（下单、撤单、调仓、清仓、下载财报）须用户确认；交易类脚本加 `--execute --confirm`



## 测试



```bash

pytest tests/test_skills_smoke.py -q

```


