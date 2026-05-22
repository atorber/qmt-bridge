---
name: qmt-bridge-feishu-doc
description: >-
  将 QMT Bridge 复盘/盈亏/分析报告同步到飞书云文档：规定云空间目录与标题命名，
  通过官方 lark-cli 与 lark-doc、lark-drive、lark-shared Skill 完成（不用仓库 scripts/ 飞书脚本）。
  在用户提到上传飞书、同步复盘文档、飞书云文档时使用。
---

# QMT Bridge 飞书云文档 Skill

> **实现状态**：规程 + [doc-registry.md](references/doc-registry.md)；IO 走 **[lark-cli](https://github.com/larksuite/cli)** 官方 CLI

## 目标

1. 先由对应 QMT Skill 生成报告（复盘、盈亏等）
2. **当日复盘**：`daily_trade_report.py --feishu-md` 导出 `reports/feishu_daily_eval.md`（**禁止** Agent 手写摘要）
3. 用 **lark-doc** / **lark-drive**（`lark-cli docs +update` 等）写入飞书

## lark-cli 首次使用（Agent）

完整步骤见 **[references/lark-cli-setup.md](references/lark-cli-setup.md)**，摘要：

```bash
npx @larksuite/cli@latest install
npx skills add larksuite/cli -y -g
lark-cli config init --new          # 链接发给用户浏览器配置
lark-cli auth login --recommend
lark-cli auth status
```

执行飞书写操作前 **MUST** 读 **lark-shared**；改 docx 读 **lark-doc**（`--api-version v2`）；改列表标题 / 文件夹读 **lark-drive**。

**不要**使用本仓库 `scripts/` 下已移除的飞书 Python 脚本；**不要**在本目录维护上传脚本。

## 云空间目录

```
QMT Bridge/
├── 每日复盘/      ← daily-eval
├── 盈亏快照/      ← daily-pnl
├── 涨跌分析/      ← return-analysis
└── 组合风控/      ← portfolio-risk
```

文件夹 token → `.env`（见 doc-registry）。

## 报告类型

| type | 子目录 | 先执行的 QMT Skill | 本地 Markdown |
|------|--------|-------------------|---------------|
| daily-eval | 每日复盘 | [execution-review](../qmt-bridge-execution-review/SKILL.md) | `reports/feishu_daily_eval.md` |
| daily-pnl | 盈亏快照 | [daily-pnl](../qmt-bridge-daily-pnl/SKILL.md) | `reports/feishu_daily_pnl.md` |
| return-analysis | 涨跌分析 | [return-analysis](../qmt-bridge-return-analysis/SKILL.md) | `reports/feishu_return_analysis.md` |
| portfolio-risk | 组合风控 | [portfolio-risk](../qmt-bridge-portfolio-risk/SKILL.md) | `reports/feishu_portfolio_risk.md` |

doc token：`reports/feishu_doc_ids.json` 或 `FEISHU_*_DOC_ID`。

## 工作流：当日复盘

详见 **[references/workflows/daily-eval-sync.md](references/workflows/daily-eval-sync.md)**。同步前必须先跑 `--feishu-md`。

**放置位置**

| 情况 | 行为 |
|------|------|
| 用户**未**指定父文档 | `wiki +node-create --as user --title "..."`（**不传** `--parent-node-token`）→ **个人知识库根** |
| 用户给出 **wiki 父页面 URL/token** | 加 `--parent-node-token <TOKEN>` 建子文档 |
| 用户要求云空间子目录 | `docs +create --folder-token ...` |
| 覆盖已有 doc | `docs +update --doc DOC_TOKEN ...` |

勿在未指定时沿用历史对话中的父节点。父 token 可选：`FEISHU_DAILY_EVAL_WIKI_PARENT_TOKEN` 或 `feishu_doc_ids.json` 的 `daily-eval-wiki-parent`。

## 提示词示例

| 场景 | 提示词 |
|------|--------|
| 复盘上传 | `把今日交易复盘同步到飞书文档`（默认知识库根新建） |
| 指定父页 | `同步到飞书 wiki 父文档 <URL> 下，新建子文档` |
| 盈亏 | `上传当日盈亏到飞书盈亏快照目录` |
| 新建 | `在飞书每日复盘目录新建一篇今日复盘` |

## 操作规程

1. `lark-cli auth status` 正常；已读 **lark-shared** + **lark-doc**
2. 运行对应 QMT Skill 脚本取数
3. 写 `reports/*.md`（`--content` 路径相对仓库根）
4. `docs +update` 或 `+create`（可先 `--dry-run`）
5. 核对云文档标题与 H1 一致
6. **只上传报告，不下单**

## 标题规范（摘要）

`QMT Bridge 当日复盘 2026-05-21 15:30:00` — 见 doc-registry。

## 安全

- 遵循 lark-cli 官方安全提示；凭证在系统密钥链，勿泄露
- 报告含交易数据，注意云文档权限范围

