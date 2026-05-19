# Agent Skills

QMT Bridge 在仓库 [`skills/`](../skills/) 目录下发布 Agent Skills，供 Cursor、Claude Code 等工具在对话中自动或手动加载，统一交易操作流程与安全规范。

## 交易 Skill

- **名称**：`qmt-bridge-trading`
- **源文件**：[skills/qmt-bridge-trading/SKILL.md](../skills/qmt-bridge-trading/SKILL.md)
- **能力**：持仓/资产/委托查询、单笔与批量下单、撤单、清仓（批量卖出可卖数量）
- **脚本**：`skills/qmt-bridge-trading/scripts/`（`trading_status.py`、`place_order.py`、`liquidate.py`），供 Agent 单次 shell 调用，减少手写代码

```bash
pip install -e .
python skills/qmt-bridge-trading/scripts/trading_status.py
```

### Cursor 快速启用

在仓库根目录：

```bash
mkdir -p .cursor/skills
ln -sf ../../skills/qmt-bridge-trading .cursor/skills/qmt-bridge-trading
```

Windows 可使用目录联接：`mklink /J .cursor\skills\qmt-bridge-trading skills\qmt-bridge-trading`。

### 安全提示

Skills 面向**真实账户**操作。Agent 在执行下单、清仓前必须向用户确认参数；勿在日志或对话中输出完整 API Key。

更多 Agent 集成方式见 [skills/README.md](../skills/README.md)。
