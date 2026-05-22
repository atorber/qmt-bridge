"""execution_review_eval 单元测试（无需 Bridge）。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "_shared"))

from execution_review_eval import build_operation_evaluation  # noqa: E402
from pnl_util import DailyPnlBreakdown, TradeDaySummary  # noqa: E402


def test_build_operation_evaluation():
    b1 = DailyPnlBreakdown(
        stock_code="600584.SH",
        current_volume=2000,
        yesterday_volume=3700,
        last_price=66.0,
        pre_close=60.0,
        daily_pnl=20000.0,
        overnight_pnl=20000.0,
        buy_pnl=None,
        sell_pnl=-100.0,
        trade_summary=TradeDaySummary(sell_volume=1700, sell_amount=110000),
        source="trades",
    )
    b2 = DailyPnlBreakdown(
        stock_code="300394.SZ",
        current_volume=900,
        yesterday_volume=500,
        last_price=355.0,
        pre_close=363.0,
        daily_pnl=-5000.0,
        overnight_pnl=None,
        buy_pnl=-2000.0,
        sell_pnl=None,
        trade_summary=TradeDaySummary(buy_volume=400, buy_amount=140000),
        source="trades",
    )
    ev = build_operation_evaluation(
        orders=[],
        trades=[],
        breakdowns=[b1, b2],
        asset={"total_asset": 900000, "cash": 5000},
        name_map={"600584.SH": "长电", "300394.SZ": "天孚"},
        cancelled_count=2,
    )
    assert ev.total_daily_pnl == 15000.0
    assert ev.overall_score >= 5
    assert len(ev.stocks) == 2
    assert any(s.operation_label == "大涨止盈" for s in ev.stocks)
    assert ev.philosophy is not None
    assert ev.philosophy.sector_summary.startswith("持仓板块")
