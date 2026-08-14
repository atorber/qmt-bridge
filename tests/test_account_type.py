"""账户类型解析单元测试。"""

from qmt_bridge.accounts import (
    build_account_type_map,
    normalize_account_type,
    resolve_account_type,
    resolve_default_trading_account,
)


def test_normalize_account_type_stock():
    assert normalize_account_type("") == ""
    assert normalize_account_type("STOCK") == ""
    assert normalize_account_type("security") == ""


def test_normalize_account_type_credit():
    assert normalize_account_type("CREDIT") == "CREDIT"
    assert normalize_account_type("3") == "CREDIT"


def test_resolve_account_type_default_credit():
    assert (
        resolve_account_type(
            "766860001037",
            server_account_id="766860001037",
            server_default_type="CREDIT",
            explicit_type="",
            type_map={},
        )
        == "CREDIT"
    )


def test_resolve_account_type_map_stock():
    assert (
        resolve_account_type(
            "755100210127",
            server_account_id="766860001037",
            server_default_type="CREDIT",
            explicit_type="",
            type_map={"755100210127": ""},
        )
        == ""
    )


def test_build_account_type_map_from_stock_credit():
    m = build_account_type_map("755100210127", "755860001037")
    assert m["755100210127"] == ""
    assert m["755860001037"] == "CREDIT"


def test_resolve_default_trading_account_defaults_to_stock():
    aid, atype = resolve_default_trading_account(
        stock_account_id="755100210127",
        credit_account_id="755860001037",
    )
    assert aid == "755100210127"
    assert atype == ""


def test_resolve_default_trading_account_credit_pref():
    aid, atype = resolve_default_trading_account(
        stock_account_id="755100210127",
        credit_account_id="755860001037",
        default_account="credit",
    )
    assert aid == "755860001037"
    assert atype == "CREDIT"


def test_resolve_default_trading_account_credit_only():
    aid, atype = resolve_default_trading_account(
        credit_account_id="755860001037",
    )
    assert aid == "755860001037"
    assert atype == "CREDIT"
