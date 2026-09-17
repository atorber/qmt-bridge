# 开发指南

常用命令在 **QMT Bridge** 仓库根目录执行。本仓 CI 只跑 API 契约测试；Agent Skills 测试在 [qmt-trading-skill](https://github.com/atorber/qmt-trading-skill)。

## 安装与依赖

```bash
pip install -e .                              # 客户端
pip install -e ".[full,desktop]"                  # 服务端 + 桌面控制面板
pip install -e ".[full,docs,dashboard]"           # 文档 / 仪表盘
```

## 服务与数据

```bash
qmt-server --port 8080 --trading              # 启动 API
qmt-scheduler                                 # 定时下载（独立进程）
qmt-desktop                                   # Windows 控制面板（需 .[desktop]）
python scripts/download_all.py                # 全量历史 + 财务
python scripts/download_all.py --periods 1m --skip-financial
```

## 文档、测试与构建

```bash
mkdocs serve -a 127.0.0.1:8001
mkdocs build -d site/
streamlit run dashboard/app.py
python -m pytest tests/ -q
python -m ruff format src/ tests/
python -m ruff check src/ tests/
python -m build
powershell -ExecutionPolicy Bypass -File packaging\windows\build.ps1              # 本机架构
powershell -ExecutionPolicy Bypass -File packaging\windows\build.ps1 -Arch x64    # x86-win
powershell -ExecutionPolicy Bypass -File packaging\windows\build.ps1 -Arch arm64  # arm-win
```

联调测试（需已启动 Bridge）：

```bash
$env:QMT_BRIDGE_LIVE = "1"; python -m pytest tests/live -m live -v
```
