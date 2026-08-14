# 开发指南

常用命令在 **QMT Bridge** 仓库根目录执行。

## 安装与依赖

```bash
pip install -e .                              # 客户端
pip install -e ".[full]"                      # 服务端
pip install -e ".[full,docs,dashboard]"       # 全部
```

## 服务与数据

```bash
qmt-server --port 8080 --trading              # 启动 API
qmt-scheduler                                 # 定时下载（独立进程）
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
```

联调测试（需已启动 Bridge）：

```bash
$env:QMT_BRIDGE_LIVE = "1"; python -m pytest tests/live -m live -v
```
