"""OpenAPI 请求样本：覆盖无法用 schema 猜到的参数组合。

键格式: ``"METHOD /path"``（path 保留 ``{param}`` 占位符）
"""

from __future__ import annotations

# 手工样本（优先于自动 schema 推断）
OPERATION_SAMPLES: dict[str, dict] = {
    "GET /api/meta/stock_list": {
        "query": {"category": "沪深A股"},
    },
    "GET /api/meta/last_trade_date": {
        "query": {"market": "SH"},
    },
    "GET /api/market/full_tick": {
        "query": {"stocks": "000001.SZ,600519.SH"},
    },
    "GET /api/market/market_data_ex": {
        "query": {
            "stocks": "000001.SZ",
            "period": "1d",
            "count": 5,
        },
    },
    "GET /api/market/local_data": {
        "query": {
            "stocks": "000001.SZ",
            "period": "1d",
            "count": 5,
        },
    },
    "GET /api/market/divid_factors": {
        "query": {"stock": "000001.SZ"},
    },
    "GET /api/market/market_data": {
        "query": {
            "stocks": "000001.SZ",
            "period": "1d",
            "count": 5,
        },
    },
    "GET /api/tick/l2_quote": {
        "query": {"stock": "000001.SZ"},
    },
    "GET /api/sector/stocks": {
        "query": {"sector": "沪深A股"},
    },
    "GET /api/calendar/trading_dates": {
        "query": {"market": "SH"},
    },
    "GET /api/financial/data": {
        "query": {
            "stocks": "000001.SZ",
            "tables": "Balance",
        },
    },
    "GET /api/instrument/detail": {
        "query": {"stock": "000001.SZ"},
    },
    "GET /api/instrument/index_weight": {
        "query": {"index_code": "000300.SH"},
    },
    "GET /api/option/list": {
        "query": {
            "undl_code": "000300.SH",
            "dedate": "20250321",
        },
    },
    "GET /api/futures/main_contract": {
        "query": {"code_market": "IF.CFE"},
    },
    "GET /api/history": {
        "query": {
            "stock": "000001.SZ",
            "period": "1d",
            "count": 5,
        },
    },
    "GET /api/history_ex": {
        "query": {
            "stocks": "000001.SZ",
            "period": "1d",
            "count": 5,
        },
    },
    "GET /api/full_tick": {
        "query": {"stocks": "000001.SZ"},
    },
    "GET /api/sector_stocks": {
        "query": {"sector": "沪深A股"},
    },
    "GET /api/instrument_detail": {
        "query": {"stock": "000001.SZ"},
    },
    "POST /api/download/history_data2": {
        "body": {
            "stocks": ["000001.SZ"],
            "period": "1d",
        },
    },
    "POST /api/download/financial_data": {
        "body": {
            "stocks": ["000001.SZ"],
            "tables": ["Balance"],
        },
    },
    "POST /api/download/financial_data2": {
        "body": {
            "stocks": ["000001.SZ"],
            "tables": ["Balance"],
        },
    },
    "POST /api/download/his_st_data": {
        "body": {
            "stocks": ["000001.SZ"],
            "period": "1d",
        },
    },
    "POST /api/download/tabular_data": {
        "body": {"tables": ["test_table"]},
    },
    "POST /api/trading/order": {
        "body": {
            "stock_code": "000001.SZ",
            "order_type": 23,
            "order_volume": 100,
            "price_type": 5,
        },
    },
    "POST /api/trading/cancel": {
        "body": {"order_id": 10001},
    },
    "POST /api/trading/batch_order": {
        "body": [
            {
                "stock_code": "000001.SZ",
                "order_type": 23,
                "order_volume": 100,
            }
        ],
    },
    "POST /api/trading/batch_cancel": {
        "body": [{"order_id": 10001}],
    },
    "POST /api/trading/order_async": {
        "body": {
            "stock_code": "000001.SZ",
            "order_type": 23,
            "order_volume": 100,
        },
    },
    "POST /api/trading/cancel_async": {
        "body": {"order_id": 10001},
    },
    "POST /api/trading/cancel_by_sysid": {
        "body": {"market": "SZ", "sysid": "test-sysid"},
    },
    "POST /api/trading/cancel_by_sysid_async": {
        "body": {"market": "SZ", "sysid": "test-sysid"},
    },
    "POST /api/credit/order": {
        "body": {
            "stock_code": "000001.SZ",
            "order_type": 23,
            "order_volume": 100,
        },
    },
    "POST /api/fund/transfer": {
        "body": {"transfer_direction": 1, "amount": 1000.0},
    },
    "POST /api/fund/secu_transfer": {
        "body": {
            "transfer_direction": 1,
            "stock_code": "000001.SZ",
            "volume": 100,
            "transfer_type": 1,
        },
    },
    "POST /api/bank/transfer_in": {
        "body": {
            "bank_no": "001",
            "bank_account": "6222000000000000",
            "balance": 1000.0,
        },
    },
    "POST /api/bank/transfer_out": {
        "body": {
            "bank_no": "001",
            "bank_account": "6222000000000000",
            "balance": 1000.0,
        },
    },
    "POST /api/bank/query_amount": {
        "body": {
            "bank_no": "001",
            "bank_account": "6222000000000000",
            "bank_pwd": "",
        },
    },
    "POST /api/trading/export_data": {
        "body": {
            "result_path": "C:\\temp\\export.csv",
            "data_type": "order",
        },
    },
    "POST /api/trading/query_data": {
        "body": {
            "result_path": "C:\\temp\\export.csv",
            "data_type": "order",
        },
    },
    "POST /api/trading/sync_transaction": {
        "body": {
            "operation": "sync",
            "data_type": "deal",
            "deal_list": [],
        },
    },
}

# 子进程内 xtdata 无法继承 mock，单独跳过
SKIP_OPERATIONS: set[str] = {
    "GET /api/market/divid_factors",
    "GET /api/market/market_data",
}

# 需要 API Key 的路径前缀
TRADING_PREFIXES: tuple[str, ...] = (
    "/api/trading/",
    "/api/credit/",
    "/api/fund/",
    "/api/bank/",
    "/api/smt/",
)
