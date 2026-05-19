"""xtquant / xtdata 桩模块，供无 QMT 环境运行 API 测试。"""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock

import pandas as pd

_SAMPLE_STOCK = "000001.SZ"
_SAMPLE_STOCKS = ["000001.SZ", "600519.SH"]
_SAMPLE_SECTOR = "沪深A股"


def _empty() -> dict:
    return {}


def _stock_list(*_args, **_kwargs) -> list[str]:
    return list(_SAMPLE_STOCKS)


def _sector_list(*_args, **_kwargs) -> list[str]:
    return [_SAMPLE_SECTOR, "沪深ETF", "沪深指数"]


def _df_by_stock(*_args, **kwargs) -> dict:
    stocks = kwargs.get("stock_list") or _SAMPLE_STOCKS
    if not stocks and _args:
        first = _args[0]
        stocks = first if isinstance(first, list) else [first]
    if not stocks:
        stocks = _SAMPLE_STOCKS
    return {code: pd.DataFrame({"close": [10.0], "open": [10.0]}) for code in stocks}


def _field_df(*_args, **_kwargs) -> dict:
    return {"close": pd.DataFrame({_SAMPLE_STOCK: [10.0]})}


def _full_tick(*_args, **kwargs) -> dict:
    codes = kwargs.get("code_list") or _SAMPLE_STOCKS
    return {code: {"lastPrice": 10.0, "volume": 100} for code in codes}


def _noop(*_args, **_kwargs):
    return None


def _zero(*_args, **_kwargs) -> int:
    return 0


def _subscribe(*_args, **_kwargs) -> int:
    return 1


# 常用 xtdata 接口返回值
_HANDLERS: dict[str, object] = {
    "get_markets": lambda *_a, **_k: [{"market": "SH"}, {"market": "SZ"}],
    "get_period_list": lambda *_a, **_k: ["1m", "5m", "1d"],
    "get_stock_list_in_sector": _stock_list,
    "get_market_last_trade_date": lambda *_a, **_k: "20250101",
    "get_sector_list": _sector_list,
    "get_sector_info": lambda *_a, **_k: {"sector_name": _SAMPLE_SECTOR},
    "get_full_tick": _full_tick,
    "get_market_data_ex": _df_by_stock,
    "get_local_data": _df_by_stock,
    "get_market_data": _field_df,
    "get_market_data3": _df_by_stock,
    "get_divid_factors": _df_by_stock,
    "get_financial_data": _df_by_stock,
    "get_financial_data_ori": _df_by_stock,
    "get_financial_table_list": lambda *_a, **_k: ["Balance", "Income"],
    "get_instrument_detail_list": lambda *_a, **_k: {
        _SAMPLE_STOCK: {"InstrumentName": "平安银行"}
    },
    "get_instrument_detail": lambda *_a, **_k: {"InstrumentName": "平安银行"},
    "get_instrument_type": lambda *_a, **_k: "stock",
    "get_ipo_info": _empty,
    "get_index_weight": lambda *_a, **_k: {_SAMPLE_STOCK: 0.01},
    "get_his_st_data": _empty,
    "get_main_contract": lambda *_a, **_k: "IF2506.CFE",
    "get_sec_main_contract": lambda *_a, **_k: "IF2506.CFE",
    "get_option_detail_data": _empty,
    "get_option_undl_data": _stock_list,
    "get_option_list": _stock_list,
    "get_his_option_list": _stock_list,
    "get_etf_list": _stock_list,
    "get_cb_info": _stock_list,
    "get_l2_quote": _empty,
    "get_l2_order": _empty,
    "get_l2_transaction": _empty,
    "get_l2_thousand_quote": _empty,
    "get_l2_thousand_orderbook": _empty,
    "get_l2_thousand_trade": _empty,
    "get_l2thousand_queue": _empty,
    "get_broker_queue_data": _empty,
    "get_order_rank": _empty,
    "get_hk_broker_dict": _empty,
    "get_full_kline": _df_by_stock,
    "get_fullspeed_orderbook": _empty,
    "get_transactioncount": _empty,
    "get_tabular_formula": _df_by_stock,
    "call_formula": lambda *_a, **_k: {"result": []},
    "call_formula_batch": lambda *_a, **_k: {"result": []},
    "generate_index_data": _zero,
    "create_formula": _zero,
    "get_quote_server_status": lambda *_a, **_k: {"status": "ok"},
    "create_sector_folder": _zero,
    "create_sector": _zero,
    "add_sector": _zero,
    "remove_stock_from_sector": _zero,
    "remove_sector": _zero,
    "reset_sector": _zero,
}


class _XtDataModule:
    """动态提供 xtdata 函数桩。"""

    def __getattr__(self, name: str):
        if name.startswith("download_"):
            return _noop
        if name.startswith("subscribe"):
            return _subscribe
        if name.startswith("unsubscribe"):
            return _noop
        handler = _HANDLERS.get(name)
        if handler is not None:
            return handler
        return _empty


def install_xtquant_mock() -> None:
    """将 xtquant 桩安装到 sys.modules（幂等）。"""
    if getattr(install_xtquant_mock, "_done", False):
        return

    xtdata = _XtDataModule()
    mock_client = MagicMock()
    mock_client.get_connect_status.return_value = True

    def _get_client():
        return mock_client

    xtdata.get_client = _get_client  # type: ignore[attr-defined]

    xtquant = types.ModuleType("xtquant")
    xtquant.__version__ = "mock"
    xtquant.xtdata = xtdata

    xttype = types.ModuleType("xtquant.xttype")

    class StockAccount:
        def __init__(self, account_id: str = ""):
            self.account_id = account_id

    xttype.StockAccount = StockAccount

    xttrader = types.ModuleType("xtquant.xttrader")

    class XtQuantTrader:
        def __init__(self, *_args, **_kwargs):
            pass

        def register_callback(self, *_args, **_kwargs):
            pass

        def start(self):
            pass

        def connect(self):
            return 0

        def subscribe(self, *_args, **_kwargs):
            return 0

        def stop(self):
            pass

        def order_stock(self, *_args, **_kwargs):
            return 10001

        def order_stock_async(self, *_args, **_kwargs):
            return 1

        def cancel_order_stock(self, *_args, **_kwargs):
            return 0

        def cancel_order_stock_async(self, *_args, **_kwargs):
            return 1

        def cancel_order_stock_sysid(self, *_args, **_kwargs):
            return 0

        def cancel_order_stock_sysid_async(self, *_args, **_kwargs):
            return 1

        def query_stock_orders(self, *_args, **_kwargs):
            return []

        def query_stock_positions(self, *_args, **_kwargs):
            return []

        def query_stock_asset(self, *_args, **_kwargs):
            return None

        def query_stock_trades(self, *_args, **_kwargs):
            return []

        def query_stock_order(self, *_args, **_kwargs):
            return None

        def query_account_status(self):
            return []

        def query_secu_account(self, *_args, **_kwargs):
            return []

        def query_account_infos(self):
            return []

        def query_new_purchase_limit(self, *_args, **_kwargs):
            return []

        def query_ipo_data(self):
            return []

        def query_com_fund(self, *_args, **_kwargs):
            return None

        def query_com_position(self, *_args, **_kwargs):
            return []

        def export_data(self, *_args, **_kwargs):
            return 0

        def query_data(self, *_args, **_kwargs):
            return []

        def sync_transaction_from_external(self, *_args, **_kwargs):
            return 0

        def fund_transfer(self, *_args, **_kwargs):
            return 0

        def bank_transfer_in(self, *_args, **_kwargs):
            return 0

        def bank_transfer_out(self, *_args, **_kwargs):
            return 0

        def bank_transfer_in_async(self, *_args, **_kwargs):
            return 1

        def bank_transfer_out_async(self, *_args, **_kwargs):
            return 1

        def query_bank_info(self, *_args, **_kwargs):
            return []

        def query_bank_amount(self, *_args, **_kwargs):
            return 0

        def query_bank_transfer_stream(self, *_args, **_kwargs):
            return []

        def ctp_transfer_option_to_future(self, *_args, **_kwargs):
            return 0

        def ctp_transfer_future_to_option(self, *_args, **_kwargs):
            return 0

        def secu_transfer(self, *_args, **_kwargs):
            return 0

        def query_credit_detail(self, *_args, **_kwargs):
            return None

        def query_stk_compacts(self, *_args, **_kwargs):
            return []

        def query_credit_slo_code(self, *_args, **_kwargs):
            return []

        def query_credit_subjects(self, *_args, **_kwargs):
            return []

        def query_credit_assure(self, *_args, **_kwargs):
            return []

        def smt_query_quoter(self, *_args, **_kwargs):
            return []

        def smt_query_compact(self, *_args, **_kwargs):
            return []

        def smt_query_order(self, *_args, **_kwargs):
            return []

        def smt_negotiate_order_async(self, *_args, **_kwargs):
            return 1

        def smt_appointment_order_async(self, *_args, **_kwargs):
            return 1

        def smt_appointment_cancel_async(self, *_args, **_kwargs):
            return 1

        def smt_compact_renewal_async(self, *_args, **_kwargs):
            return 1

        def smt_compact_return_async(self, *_args, **_kwargs):
            return 1

    xttrader.XtQuantTrader = XtQuantTrader

    sys.modules["xtquant"] = xtquant
    sys.modules["xtquant.xtdata"] = xtdata
    sys.modules["xtquant.xttype"] = xttype
    sys.modules["xtquant.xttrader"] = xttrader

    install_xtquant_mock._done = True  # type: ignore[attr-defined]
