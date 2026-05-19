# Agent Skills

本目录包含与 **QMT Bridge** 配套的 [Agent Skills](https://docs.cursor.com/context/skills)（`SKILL.md` 格式），随仓库一起发布。克隆或 `pip install` 源码包后均可使用，便于在 Cursor、Claude Code、Codex 等 Agent 中统一指导交易与行情相关操作。

## 可用 Skills

| Skill | 路径 | 说明 |
|-------|------|------|
| **qmt-bridge-trading** | [`qmt-bridge-trading/SKILL.md`](qmt-bridge-trading/SKILL.md) | 持仓/资产查询、下单、批量下单、撤单、清仓 |

**可执行脚本**（`qmt-bridge-trading/scripts/`，需 `pip install -e .`）：

| 脚本 | 说明 |
|------|------|
| `trading_status.py` | 只读：health、账户、持仓与资产摘要 |
| `place_order.py` | 单笔下单（默认预览，`--execute --confirm` 提交） |
| `liquidate.py` | 清仓（默认预览，`--execute --confirm` 提交） |

后续可在此目录新增更多 skill（如仅行情、数据下载等），保持「一 skill 一子目录」。

## 在各 Agent 中使用

### Cursor（推荐：项目级）

将 skill 链接到 Cursor 项目目录，Agent 会自动根据 `description` 匹配，也可在对话中 `@qmt-bridge-trading` 引用：

```bash
# 在仓库根目录执行（仅需一次）
mkdir -p .cursor/skills
# Linux / macOS
ln -sf ../../skills/qmt-bridge-trading .cursor/skills/qmt-bridge-trading
```

Windows（PowerShell，管理员或已开启开发者模式）：

```powershell
New-Item -ItemType Directory -Force -Path .cursor\skills
cmd /c mklink /J .cursor\skills\qmt-bridge-trading skills\qmt-bridge-trading
```

不创建链接时，也可直接引用文件：`@skills/qmt-bridge-trading/SKILL.md`。

### Claude Code

在仓库根目录的 `CLAUDE.md` 或用户 `~/.claude/CLAUDE.md` 中说明：

```markdown
交易相关任务请遵循 skills/qmt-bridge-trading/SKILL.md 中的流程与安全规范。
```

或将 `skills/qmt-bridge-trading` 加入 Claude Code 的 skills 搜索路径（若你的版本支持项目 skills 目录）。

### 其他 Agent / 自定义编排

1. 将 `skills/<name>/SKILL.md` 全文或路径写入 system prompt / 工具说明；
2. 要求 Agent 在调用 `/api/trading/*` 或 `QMTClient` 交易方法前读取该文件；
3. 连接信息从环境变量 `QMT_BRIDGE_HOST`、`QMT_BRIDGE_PORT`、`QMT_BRIDGE_API_KEY` 读取（与 [配置参考](../docs/configuration.md) 一致）。

## 前置条件

Skills 描述的是 **如何调用已运行的 QMT Bridge 服务**，不包含启动 QMT 客户端本身。使用前请确认：

- Windows 端 QMT 已登录，Bridge 已启动（`just serve` 或 `qmt-server --trading`）；
- 交易类操作已配置 `QMT_BRIDGE_API_KEY`；
- Agent 运行环境能访问 Bridge 的 HTTP 地址（通常为局域网 IP）。

## 贡献新 Skill

1. 新建 `skills/<skill-name>/SKILL.md`，YAML frontmatter 含 `name`、`description`（第三人称，写明触发场景）；
2. 正文保持精简，API 细节引用 `docs/rest-api.md` 与 `src/qmt_bridge/client/`；
3. 在本 README 的表格中登记；
4. 交易类 skill 必须包含「用户确认」与「勿泄露 API Key」等安全条款。

## 版本

Skills 与仓库版本同步更新，无独立版本号。重大 API 变更时请同步修改对应 `SKILL.md`。
