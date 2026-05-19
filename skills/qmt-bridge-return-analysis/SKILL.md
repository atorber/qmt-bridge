---
name: qmt-bridge-return-analysis
description: >-
  通过 QMT Bridge 查询单只或多只股票的 1/2/3/4/5/10/30 个交易日累计涨幅，
  并基于连续 10 日（可配置）日 K 线形态统计下一交易日收涨概率。在用户提到
  累计涨幅、N日涨幅、涨跌概率、形态胜率、阶段强弱时使用。只读。
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
3. 输出汇总表 + 分标的累计涨幅表 + 概率指标
4. **只读**，不下单；概率为历史统计，不构成预测或投资建议

## 安全

- `--codes` 只读，默认无需 API Key；`--holdings` 需 API Key（读持仓）

## 参考

- [qmt-bridge-market-watch](../qmt-bridge-market-watch/SKILL.md) · [qmt-bridge-sector-theme](../qmt-bridge-sector-theme/SKILL.md)
- `docs/rest-api.md`
