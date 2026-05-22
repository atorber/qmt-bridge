# 当日复盘 → 飞书云文档

**前置**：[lark-cli-setup.md](../lark-cli-setup.md)（安装、`config init`、`auth login`）。执行前读 **lark-shared**、**lark-doc**；知识库节点读 **lark-wiki**。

## 固定流程（必读）

执行「今日复盘 / 同步飞书」时 **必须** 按下列顺序，**禁止** Agent 手写或缩写 `reports/feishu_daily_eval.md`：

1. **拉取 + 导出 Markdown**（一步完成，正文结构由脚本固定）
2. **新建或更新** 飞书 docx（`lark-cli`，正文来自上一步文件）
3. （可选）同步云空间列表标题、记入本地 doc id

正文丰富度与终端复盘一致（委托表、成交、按标的汇总、完整操作评价与交易观对照）。此前简版多因跳过 `--feishu-md`、由 Agent 摘要导致。

## 1. 拉取复盘并导出 Markdown（QMT）

```bash
cd <qmt-bridge 仓库根>

python skills/qmt-bridge-execution-review/scripts/daily_trade_report.py \
  --host 127.0.0.1 --port 8080 --api-key KEY \
  --feishu-md

# 可选：量能分区
#   --market-turnover-yi 12500
# QMT 日 K 异常时：
#   --no-philosophy-fetch
```

- `--feishu-md`：写入 `reports/feishu_daily_eval.md`（UTF-8）
- `--feishu-md /path/to/custom.md`：指定路径
- 与 `--json` 可并存；**同步飞书前必须先有本步骤产物**
- H1 / 云文档标题由 `feishu_doc.format_title` 生成，例：`# QMT Bridge 当日复盘 2026-05-22 14:30:00`

## 2. 正文来源（禁止手写）

| ✅ 必须 | ❌ 禁止 |
|--------|--------|
| 使用 §1 生成的 `reports/feishu_daily_eval.md` | Agent 根据终端输出自行整理摘要 |
| `docs +update --content @reports/feishu_daily_eval.md` | 删减「五、当日操作评价」各小节 |

章节结构（脚本固定）：

1. 统计概览  
2. 当日委托（表格 + 滑点）  
3. 当日成交  
4. 按标的成交汇总  
5. 当日操作评价（交易观、分标的、明日纪律等）

## 3. 放置位置（Agent 决策）

| 用户意图 | 做法 |
|----------|------|
| **未指定父文档/目录**（默认） | 在**知识库根**新建节点（见 §4A） |
| **给出飞书 wiki 父页面 URL 或 token** | 在该父节点下新建子文档（见 §4B） |
| **要求云空间「每日复盘」文件夹** | `docs +create --folder-token`（见 §4C） |
| **要求覆盖已有某篇** | 仅 `docs +update`（§5），不新建节点 |

**不要**在未获用户指定时，擅自使用历史对话里的某个 `parent_node_token`。

父节点 token 解析：

- URL `https://<host>/wiki/<TOKEN>` → `--parent-node-token <TOKEN>`
- 或 `lark-cli wiki +node-get --token "<URL或TOKEN>" --as user` 核对标题

可选配置（本地，非默认）：

- 环境变量 `FEISHU_DAILY_EVAL_WIKI_PARENT_TOKEN`
- `reports/feishu_doc_ids.json` 的 `daily-eval-wiki-parent`

仅当用户**未**在对话中指定父文档、但希望长期固定父节点时，才读上述配置。

## 4. 新建文档

标题与 Markdown H1 一致（可从 `reports/feishu_daily_eval.md` 首行 `# ...` 读取）。

### 4A. 默认：知识库根（推荐按次新建）

`user` 身份下**不传** `--parent-node-token` 时，`wiki +node-create` 落在**个人知识库根**（`my_library`）。

```bash
lark-cli wiki +node-create --as user \
  --title "QMT Bridge 当日复盘 2026-05-22 14:30:00"

lark-cli docs +update --api-version v2 --doc OBJ_TOKEN --as user \
  --command overwrite --doc-format markdown \
  --content @reports/feishu_daily_eval.md
```

返回字段：`obj_token`（docx）、`node_token`（wiki 入口 URL 用此 token）。

### 4B. 用户指定：某 wiki 父页面下的子文档

```bash
lark-cli wiki +node-create --as user \
  --parent-node-token PARENT_WIKI_TOKEN \
  --title "QMT Bridge 当日复盘 2026-05-22 14:30:00"

lark-cli docs +update --api-version v2 --doc OBJ_TOKEN --as user \
  --command overwrite --doc-format markdown \
  --content @reports/feishu_daily_eval.md
```

### 4C. 云空间子目录（Drive 文件夹）

```bash
lark-cli docs +create --api-version v2 --doc-format markdown --as user \
  --folder-token FEISHU_FOLDER_DAILY_EVAL_TOKEN \
  --title "QMT Bridge 当日复盘 2026-05-22 14:30:00" \
  --content @reports/feishu_daily_eval.md
```

## 5. 滚动更新（覆盖已有 docx）

`DOC_TOKEN` ← `reports/feishu_doc_ids.json` 的 `daily-eval` 或 `FEISHU_DAILY_EVAL_DOC_ID`。

```bash
# 先 §1 重新导出 Markdown，再更新
lark-cli docs +update --api-version v2 --doc DOC_TOKEN --as user \
  --command overwrite --doc-format markdown \
  --content @reports/feishu_daily_eval.md
```

预览：加 `--dry-run`。

## 6. 同步云空间列表标题

与 H1 相同。按 **lark-drive** Skill：`drive files patch`（`type=docx`，`new_title` 为 H1 文本）。

## 7. 本地记录（可选）

按次新建后，可将 `obj_token` / `node_token` 记入 `reports/feishu_wiki_daily_eval.json` 或 `feishu_doc_ids.json`，供下次滚动更新。**勿将真实 token 提交 git**（`reports/` 已 ignore）。
