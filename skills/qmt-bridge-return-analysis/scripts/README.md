# qmt-bridge-return-analysis 脚本

| 脚本 | 状态 | 说明 |
|------|------|------|
| `return_probability_analysis.py` | ✅ | 累计涨幅、形态概率（自适应）、量价概率 |

```bash
just agent-return-analysis --holdings --host 127.0.0.1 --port 8080 --api-key KEY
just agent-return-analysis --codes 000001.SZ,600519.SH
just agent-return-analysis --codes 300394.SZ --pattern-len 9 --json
```
