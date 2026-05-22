"""trading_philosophy 单元测试（无需 Bridge）。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "_shared"))

from trading_philosophy import (  # noqa: E402
    IntradayRange,
    apply_trading_philosophy,
    classify_buy_timing,
    classify_sector,
    classify_volume_zone,
    is_chase_rise_buy_by_price,
)


class _Stock:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def test_classify_sector():
    assert classify_sector("300394.SZ", "天孚通信") == "科技"
    assert classify_sector("601318.SH", "中国平安") == "大金融"


def test_volume_zone():
    z = classify_volume_zone(9000)
    assert z is not None and z.label == "谨慎区"
    z2 = classify_volume_zone(12000)
    assert z2 is not None and z2.label == "适度参与区"


def test_chase_by_high_buy_price():
    """买入价贴近当日高点 → 追涨。"""
    day = IntradayRange(low=100.0, high=110.0, pre_close=100.0)
    assert is_chase_rise_buy_by_price(109.0, day) is True
    label, _, _ = classify_buy_timing(109.0, day, pct_chg=8.0)
    assert label == "追涨加仓"


def test_dip_success_close_up():
    """买均明显低于收盘、收盘大涨 → 低吸成功，不判追涨。"""
    day = IntradayRange(
        low=550.0, high=600.0, pre_close=560.0, last=598.0
    )
    label, note, pos = classify_buy_timing(574.92, day, pct_chg=9.0)
    assert label == "低吸加仓"
    assert is_chase_rise_buy_by_price(574.92, day) is False
    assert "低吸成功" in note or "上行" in note

    st = _Stock(
        stock_code="300502.SZ",
        stock_name="新易盛",
        pct_chg=9.0,
        buy_volume=100,
        sell_volume=0,
        operation_label="低吸加仓",
        buy_avg=574.92,
        intraday=day,
    )
    r = apply_trading_philosophy(
        stocks=[st],
        name_map={"300502.SZ": "新易盛"},
        total_asset=1_000_000,
        cash=50_000,
        order_count=3,
        cancelled_count=0,
        buy_avg_by_code={"300502.SZ": 574.92},
        intraday_by_code={"300502.SZ": day},
    )
    assert not any("追涨" in v for v in r.violations)
    assert any("低吸成功" in a for a in r.aligned)


def test_moderate_close_up_not_chase_without_range():
    """无高低价时，收盘涨 4%  alone 不触发旧逻辑追涨。"""
    st = _Stock(
        stock_code="300502.SZ",
        stock_name="新易盛",
        pct_chg=4.08,
        buy_volume=100,
        sell_volume=0,
        operation_label="顺势加仓",
        buy_avg=574.92,
        intraday=IntradayRange(pre_close=560.0),
    )
    r = apply_trading_philosophy(
        stocks=[st],
        name_map={"300502.SZ": "新易盛"},
        total_asset=1_000_000,
        cash=50_000,
        order_count=3,
        cancelled_count=0,
        buy_avg_by_code={"300502.SZ": 574.92},
        intraday_by_code={"300502.SZ": IntradayRange(pre_close=560.0)},
    )
    assert not any("收盘大涨" in v for v in r.violations)
    assert not any("忌追涨" in v and "300502" in v for v in r.violations)
