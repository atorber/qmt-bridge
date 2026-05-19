# qmt-bridge-daily-pnl 脚本

| 脚本 | 状态 | 说明 |
|------|------|------|
| `daily_pnl_snapshot.py` | ✅ | 表格化账户概览+个股盈亏、已清仓、`--json` |

```bash
just agent-daily-pnl --port 8080 --api-key KEY
just agent-daily-pnl --no-tick-fallback
just agent-daily-pnl --min-pnl 500
```
