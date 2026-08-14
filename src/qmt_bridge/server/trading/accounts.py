"""兼容导入：实现已迁至 ``qmt_bridge.accounts``。"""

from qmt_bridge.accounts import (
    build_account_type_map,
    normalize_account_type,
    resolve_account_type,
    resolve_default_trading_account,
)

__all__ = [
    "build_account_type_map",
    "normalize_account_type",
    "resolve_account_type",
    "resolve_default_trading_account",
]
