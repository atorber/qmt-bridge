"""XtTraderManager 测试桩，替代真实 miniQMT 连接。"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock


def _position(account_id: str) -> SimpleNamespace:
    return SimpleNamespace(
        account_id=account_id,
        stock_code="000001.SZ",
        volume=1000,
        can_use_volume=1000,
        frozen_volume=0,
        open_price=10.0,
        market_value=10000.0,
    )


def _asset(account_id: str) -> SimpleNamespace:
    return SimpleNamespace(
        account_id=account_id,
        cash=100000.0,
        frozen_cash=0.0,
        market_value=50000.0,
        total_asset=150000.0,
    )


def _order(account_id: str, order_id: int = 10001) -> SimpleNamespace:
    return SimpleNamespace(
        account_id=account_id,
        order_id=order_id,
        stock_code="000001.SZ",
        order_type=23,
        order_volume=100,
        price_type=5,
        price=10.0,
        order_status=50,
    )


class TraderManagerStub:
    """与 XtTraderManager 同接口的轻量桩。"""

    def __init__(self, mini_qmt_path: str = "", account_id: str = "12345678"):
        self.mini_qmt_path = mini_qmt_path
        self.account_id = account_id
        self._trader = MagicMock()
        self._account = SimpleNamespace(account_id=account_id)
        self._callback = MagicMock()

    def connect(self) -> None:
        return None

    def disconnect(self) -> None:
        self._trader = None

    def order(
        self,
        stock_code: str,
        order_type: int,
        order_volume: int,
        price_type: int = 5,
        price: float = 0.0,
        strategy_name: str = "",
        order_remark: str = "",
        account_id: str = "",
    ) -> int:
        return 10001

    def order_async(self, *args, **kwargs) -> int:
        return 1

    def cancel_order(self, order_id: int, account_id: str = "") -> int:
        return 0

    def cancel_order_async(self, order_id: int, account_id: str = "") -> int:
        return 1

    def cancel_order_stock_sysid(
        self, market: str, sysid: str, account_id: str = ""
    ) -> int:
        return 0

    def cancel_order_stock_sysid_async(
        self, market: str, sysid: str, account_id: str = ""
    ) -> int:
        return 1

    def query_orders(self, account_id: str = "", cancelable_only: bool = False):
        return [_order(account_id or self.account_id)]

    def query_positions(self, account_id: str = ""):
        return [_position(account_id or self.account_id)]

    def query_asset(self, account_id: str = ""):
        return _asset(account_id or self.account_id)

    def query_trades(self, account_id: str = ""):
        return []

    def query_order_detail(self, order_id: int = 0, account_id: str = ""):
        return _order(account_id or self.account_id, order_id or 10001)

    def query_single_order(self, order_id: int, account_id: str = ""):
        return _order(account_id or self.account_id, order_id)

    def query_single_trade(self, trade_id: int, account_id: str = ""):
        return None

    def query_single_position(self, stock_code: str, account_id: str = ""):
        pos = _position(account_id or self.account_id)
        pos.stock_code = stock_code
        return pos

    def credit_order(self, *args, **kwargs) -> int:
        return 10002

    def query_credit_positions(self, account_id: str = ""):
        return []

    def query_credit_detail(self, account_id: str = ""):
        return _asset(account_id or self.account_id)

    def query_stk_compacts(self, account_id: str = ""):
        return []

    def query_credit_slo_code(self, account_id: str = ""):
        return []

    def query_credit_subjects(self, account_id: str = ""):
        return []

    def query_credit_assure(self, account_id: str = ""):
        return []

    def fund_transfer(self, *args, **kwargs) -> int:
        return 0

    def bank_transfer_in(self, *args, **kwargs) -> int:
        return 0

    def bank_transfer_out(self, *args, **kwargs) -> int:
        return 0

    def bank_transfer_in_async(self, *args, **kwargs) -> int:
        return 1

    def bank_transfer_out_async(self, *args, **kwargs) -> int:
        return 1

    def query_bank_info(self, account_id: str = ""):
        return []

    def query_bank_amount(self, *args, **kwargs) -> int:
        return 0

    def query_bank_transfer_stream(self, *args, **kwargs):
        return []

    def ctp_transfer_option_to_future(self, *args, **kwargs) -> int:
        return 0

    def ctp_transfer_future_to_option(self, *args, **kwargs) -> int:
        return 0

    def secu_transfer(self, *args, **kwargs) -> int:
        return 0

    def smt_query_quoter(self, account_id: str = ""):
        return []

    def smt_query_compact(self, account_id: str = ""):
        return []

    def smt_query_order(self, account_id: str = ""):
        return []

    def smt_negotiate_order_async(self, *args, **kwargs) -> int:
        return 1

    def smt_appointment_order_async(self, *args, **kwargs) -> int:
        return 1

    def smt_appointment_cancel_async(self, *args, **kwargs) -> int:
        return 1

    def smt_compact_renewal_async(self, *args, **kwargs) -> int:
        return 1

    def smt_compact_return_async(self, *args, **kwargs) -> int:
        return 1

    def query_new_purchase_limit(self, account_id: str = ""):
        return []

    def query_ipo_data(self):
        return []

    def get_account_status(self, account_id: str = ""):
        return {"connected": True}

    def query_account_status(self):
        return [{"status": "ok"}]

    def query_secu_account(self, account_id: str = ""):
        return []

    def query_account_infos(self):
        return [{"account_id": self.account_id}]

    def query_com_fund(self, account_id: str = ""):
        return None

    def query_com_position(self, account_id: str = ""):
        return []

    def export_data(self, *args, **kwargs) -> int:
        return 0

    def query_data(self, *args, **kwargs):
        return []

    def sync_transaction_from_external(self, *args, **kwargs) -> int:
        return 0
