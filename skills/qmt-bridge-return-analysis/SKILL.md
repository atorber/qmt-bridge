---
name: qmt-bridge-return-analysis
description: >-
  通过 QMT Bridge 分析 1/2/3/4/5/10/30 日累计涨幅、形态/量价涨跌概率，
  并输出下一交易日操作策略与观察点。支持 --holdings 自动读持仓、缺 K 线则下载。
  在用户提到持仓阶段强弱、N日涨幅、涨跌概率、量价、明日怎么观察时使用。只读。
---

# QMT Bridge 累计涨幅与涨跌概率 Skill

> **实现状态**：✅ `return_probability_analysis.py` 可用

## 目标

回答：

1. 指定股票在 **1、2、3、4、5、10、30 个交易日**上的收盘累计涨幅（%）
2. 基于 **近 10 个交易日**日 K 涨跌形态 + 更长历史回测，给出 **下一交易日收涨的条件概率**；样本不足时自动 **缩短形态 / 放宽 1 位 / 小样本收缩估计**
3. 结合 **连续多日成交量**（相对 5 日均量、3 日量增、量价状态）评估涨跌概率（统计描述，非投资建议）

## 脚本

| 脚本 | 作用 |
|------|------|
| `scripts/return_probability_analysis.py` | `--codes` 或 `--holdings`；缺 K 自动下载 |

```bash
# 当前持仓一键分析（需 API Key）
just agent-return-analysis --holdings --host 127.0.0.1 --port 8080 --api-key YOUR_KEY

just agent-return-analysis --codes 000001.SZ,600519.SH --host 127.0.0.1 --port 8080
python skills/qmt-bridge-return-analysis/scripts/return_probability_analysis.py \
  --codes 300394.SZ,688008.SH --json
```

| 参数 | 说明 |
|------|------|
| `--codes` | 逗号分隔股票代码（与 `--holdings` 二选一） |
| `--holdings` | 从账户持仓读取标的；缺日 K 时自动 `download_batch` |
| `--download-start` | 自动补 K 起始日（默认 `20240101`） |
| `--skip-download` | 不自动下载日 K |
| `--count` | 拉取日 K 根数（默认 150） |
| `--dividend-type` | 复权：`front` / `none` / `back` 等 |
| `--pattern-len` | 形态匹配长度（默认 9 日） |
| `--json` | JSON 输出 |
| `--no-detail` | 不展示近 10 日逐日表 |
| `--no-strategy` | 不输出下一交易日策略与观察点 |

## 提示词示例（可复制）

优先引导 Agent 执行 `just agent-return-analysis` 或对应 `python .../return_probability_analysis.py`。

| 场景 | 提示词 |
|------|--------|
| **持仓一键（推荐）** | `评估当前持仓的 1/5/10/30 日累计涨幅、量价涨跌概率，并总结明日操作策略与观察点` |
| | `用 return-analysis skill 跑 --holdings，缺 K 线自动下载` |
| 指定标的 | `分析 300394.SZ、688008.SH 的阶段涨幅和近 10 日上涨概率` |
| | `这几只股票 1 日、5 日、30 日涨幅各多少，谁更强` |
| 量价 | `结合成交量看持仓明日收涨概率和放量确认度` |
| | `哪些持仓近 3 日量价形态偏强，历史次日统计如何` |
| 形态 | `用 9 日 K 线形态统计下一日收涨概率，样本不够就缩短形态` |
| 明日计划 | `根据持仓报告，给每只写明日观察点和一日策略（不荐股）` |
| | `组合层面：谁 30 日强、谁昨日回调大，明天优先盯什么` |
| 机器可读 | `持仓涨幅概率分析，输出 JSON`（加 `--json`） |

**Agent 执行要点**：`--holdings` 需 `--host 127.0.0.1` 与 API Key；`.env` 里 `QMT_BRIDGE_HOST=0.0.0.0` 时客户端仍连 `127.0.0.1`。

## 主要 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/market/market_data_ex` | 日 K（`period=1d`） |
| GET | `/api/utility/batch_stock_name` | 中文名称 |

## 计算说明

- **N 日累计涨幅**：`close[-1] / close[-1-N] - 1`（交易日收盘）
- **近 10 日收涨占比**：最近 10 个日收益率中收涨天数比例
- **形态条件概率**：取最近 `pattern_len` 日的涨跌方向序列匹配历史；样本不足时依次 **缩短至 3 日 → 允许 1 位不匹配 → 向历史基准收缩**（输出会标注 `缩短形态/放宽1位/小样本收缩`）
- **量价状态概率**：近 3 日「涨/跌 + 放量/缩量/平量」组合在历史中的下一日收涨比例
- **收涨放量→次日**：历史「收涨且量比≥1.15（相对5日均量）」后次日收涨比例
- **连增3日量→次日**：连续 3 日成交量递增后次日收涨比例
- **近10收涨放量占比**：近 10 日收涨日中，成交量高于 5 日均量的天数占比（量能确认度）

## 规程

1. 确认 Bridge 可用；`--holdings` 需配置 `QMT_BRIDGE_API_KEY`
2. 持仓模式：读 `query_positions` → `market_data_ex`；不足则 `download_batch` 后重试
3. 输出汇总表 + 分标的累计涨幅表 + 概率指标 + **下一交易日策略与观察点**（`--no-strategy` 可关闭）
4. **只读**，不下单；概率为历史统计，不构成预测或投资建议

## 安全

- `--codes` 只读，默认无需 API Key；`--holdings` 需 API Key（读持仓）

## 参考

- [qmt-bridge-market-watch](../qmt-bridge-market-watch/SKILL.md) · [qmt-bridge-sector-theme](../qmt-bridge-sector-theme/SKILL.md)
- `docs/rest-api.md`
