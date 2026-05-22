# 飞书云文档目录与标题规范

本文件为 `qmt-bridge-feishu-doc` 的权威说明。标题辅助函数见 [`skills/_shared/feishu_doc.py`](../../_shared/feishu_doc.py)（仅规范，不含上传逻辑）。

**上传**：Agent 使用 **lark-cli** + **lark-doc** / **lark-drive** Skill，见 [workflows/daily-eval-sync.md](workflows/daily-eval-sync.md)。

## 云空间目录结构

```
QMT Bridge/                          # FEISHU_QMT_BRIDGE_FOLDER_TOKEN（根目录，可选）
├── 每日复盘/                        # FEISHU_FOLDER_DAILY_EVAL_TOKEN
├── 盈亏快照/                        # FEISHU_FOLDER_DAILY_PNL_TOKEN
├── 涨跌分析/                        # FEISHU_FOLDER_RETURN_ANALYSIS_TOKEN
└── 组合风控/                        # FEISHU_FOLDER_PORTFOLIO_RISK_TOKEN
```

## 文档类型

| type | 云空间子目录 | 标题前缀 | 本地 Markdown | 数据来源 Skill |
|------|-------------|----------|---------------|----------------|
| `daily-eval` | 每日复盘 | `QMT Bridge 当日复盘` | `reports/feishu_daily_eval.md`（`daily_trade_report.py --feishu-md`） | execution-review |
| `daily-pnl` | 盈亏快照 | `QMT Bridge 当日盈亏` | `reports/feishu_daily_pnl.md` | daily-pnl |
| `return-analysis` | 涨跌分析 | `QMT Bridge 涨跌分析` | `reports/feishu_return_analysis.md` | return-analysis |
| `portfolio-risk` | 组合风控 | `QMT Bridge 组合风险` | `reports/feishu_portfolio_risk.md` | portfolio-risk |

## 标题规范

```
{标题前缀} {主题} {同步时刻}
```

| 字段 | 说明 | 示例 |
|------|------|------|
| 标题前缀 | 上表固定字符串 | `QMT Bridge 当日复盘` |
| 主题 | 交易日 `YYYY-MM-DD`，或分析范围 | `2026-05-21` / `持仓` |
| 同步时刻 | 上传时分秒；与交易日同日只写一次日期 | `15:30:00` |

示例：`QMT Bridge 当日复盘 2026-05-21 15:30:00`

正文元数据：**交易日**、**同步时间**（完整 `YYYY-MM-DD HH:MM:SS`）。

## 更新策略

| 模式 | lark-cli | 行为 |
|------|----------|------|
| **滚动更新** | `docs +update --command overwrite` | 覆盖固定 docx |
| **按次新建** | `docs +create --folder-token ...` | 在子目录新建一篇 |

## doc token 配置

1. 环境变量 `FEISHU_DAILY_EVAL_DOC_ID` 等（滚动更新用）  
2. `reports/feishu_doc_ids.json`（可复制 `feishu_doc_ids.example.json`）  
3. 遗留 `reports/feishu_daily_eval_doc_id.txt`（仅 daily-eval）

### wiki 父节点（可选，非默认）

| 键 / 环境变量 | 说明 |
|---------------|------|
| `daily-eval-wiki-parent` | 仅当用户**未**在对话指定父文档、且希望长期固定父节点时使用 |
| `FEISHU_DAILY_EVAL_WIKI_PARENT_TOKEN` | 同上 |

**默认**：不传父节点 → `wiki +node-create` 落在个人知识库根。用户当场给的 wiki URL **优先**于上述配置。

## lark-cli 要点

官方 CLI：[larksuite/cli](https://github.com/larksuite/cli)。环境配置见 [lark-cli-setup.md](lark-cli-setup.md)。

- 安装：`npx @larksuite/cli@latest install`；Skills：`npx skills add larksuite/cli -y -g`
- `docs +create` / `docs +update` 必须 `--api-version v2`；复盘上传建议 `--as user`
- `--content @reports/feishu_daily_eval.md`：**在仓库根执行**，路径相对当前目录
- 列表标题：**lark-drive** → `drive files patch`（`file_token` = docx token，`type=docx`）
- 写操作可先 `--dry-run` 预览

## 权限

执行前阅读 **lark-shared**（所有 lark-* Skill 的前置）。失败时 `lark-cli auth login --recommend` 或 `auth check`。
