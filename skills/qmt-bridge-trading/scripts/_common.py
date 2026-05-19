"""Agent 交易脚本公共模块：环境加载、客户端构造、输出格式化。"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

# 仓库根目录（含 pyproject.toml）
_REPO_ROOT = Path(__file__).resolve().parents[3]


def load_env_files() -> None:
    """从仓库根目录与当前工作目录加载 .env（简单 KEY=VALUE 解析）。"""
    for path in (_REPO_ROOT / ".env", Path.cwd() / ".env"):
        if not path.is_file():
            continue
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def add_client_args(parser) -> None:
    """为 argparse 添加连接参数（默认读环境变量）。"""
    parser.add_argument(
        "--host",
        default=None,
        help="Bridge 主机（默认 QMT_BRIDGE_HOST 或 127.0.0.1）",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Bridge 端口（默认 QMT_BRIDGE_PORT 或 8000）",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="API Key（默认 QMT_BRIDGE_API_KEY）",
    )
    parser.add_argument(
        "--account-id",
        default=None,
        help="资金账号（默认 QMT_BRIDGE_TRADING_ACCOUNT_ID 或空）",
    )


def resolve_connection(args) -> tuple[str, int, str, str]:
    """解析 host/port/api_key/account_id。"""
    host = args.host or os.environ.get("QMT_BRIDGE_HOST", "127.0.0.1")
    port = args.port if args.port is not None else int(os.environ.get("QMT_BRIDGE_PORT", "8000"))
    api_key = args.api_key if args.api_key is not None else os.environ.get("QMT_BRIDGE_API_KEY", "")
    account_id = (
        args.account_id
        if args.account_id is not None
        else os.environ.get("QMT_BRIDGE_TRADING_ACCOUNT_ID", "")
    )
    return host, port, api_key, account_id


def make_client(args):
    """构造 QMTClient；缺少依赖或 Key 时退出。"""
    try:
        from qmt_bridge import QMTClient
    except ImportError:
        print(
            "错误: 未安装 qmt-bridge。请在仓库根目录执行: pip install -e .",
            file=sys.stderr,
        )
        sys.exit(2)

    host, port, api_key, account_id = resolve_connection(args)
    if not api_key:
        print(
            "错误: 未设置 API Key。请配置 QMT_BRIDGE_API_KEY 或传入 --api-key",
            file=sys.stderr,
        )
        sys.exit(2)

    client = QMTClient(host=host, port=port, api_key=api_key)
    return client, account_id


def unwrap_data(resp: Any) -> Any:
    """统一取出响应中的 data 字段。"""
    if isinstance(resp, dict) and "data" in resp:
        return resp["data"]
    return resp


def call_api(func, *args, **kwargs) -> Any:
    """调用客户端方法并处理 HTTP 错误。"""
    import urllib.error

    try:
        return func(*args, **kwargs)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:800]
        print(f"HTTP {exc.code}: {body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as exc:
        print(f"连接失败: {exc.reason}", file=sys.stderr)
        sys.exit(1)


def fmt_num(value: Any, digits: int = 2) -> str:
    if value is None:
        return "-"
    try:
        return f"{float(value):,.{digits}f}"
    except (TypeError, ValueError):
        return str(value)
