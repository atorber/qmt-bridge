"""交易账户类型解析（普通证券 / 信用两融等）。

纯函数模块，不依赖 FastAPI / xtquant，供服务端与 Agent Skills 共用。
"""

from __future__ import annotations


def normalize_account_type(raw: str) -> str:
    """将配置归一化为 StockAccount 第二参数；普通户返回空串。"""
    t = (raw or "").strip().upper()
    if t in ("", "STOCK", "SECURITY", "SECURITY_ACCOUNT", "2"):
        return ""
    if t in ("CREDIT", "CREDIT_ACCOUNT", "3"):
        return "CREDIT"
    return t


def resolve_account_type(
    account_id: str,
    *,
    server_account_id: str,
    server_default_type: str,
    explicit_type: str,
    type_map: dict[str, str],
) -> str:
    """确定 query/order 使用的 StockAccount 类型。"""
    if explicit_type:
        return normalize_account_type(explicit_type)
    aid = (account_id or "").strip()
    if aid and aid in type_map:
        return type_map[aid]
    if not aid or aid == (server_account_id or "").strip():
        return normalize_account_type(server_default_type)
    return ""


def build_account_type_map(
    stock_account_id: str = "",
    credit_account_id: str = "",
) -> dict[str, str]:
    """由普通户/信用户 ID 合成 account_id → 类型表。"""
    out: dict[str, str] = {}
    stock = (stock_account_id or "").strip()
    credit = (credit_account_id or "").strip()
    if stock:
        out[stock] = ""
    if credit:
        out[credit] = "CREDIT"
    return out


def resolve_default_trading_account(
    *,
    stock_account_id: str = "",
    credit_account_id: str = "",
    default_account: str = "",
) -> tuple[str, str]:
    """解析默认订阅/API 账户，返回 (account_id, account_type)。默认普通户。"""
    stock = (stock_account_id or "").strip()
    credit = (credit_account_id or "").strip()
    pref = (default_account or "stock").strip().upper()

    if pref == "CREDIT" and credit:
        return credit, "CREDIT"
    if stock:
        return stock, ""
    if credit:
        return credit, "CREDIT"
    return "", ""
