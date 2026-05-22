"""execution_review_feishu_md 单元测试（无需 Bridge）。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "_shared"))

from execution_review_eval import DailyOperationEval, StockOpEval  # noqa: E402
from trading_philosophy import PhilosophyCheckResult, VolumeZone  # noqa: E402
from execution_review_feishu_md import build_daily_eval_feishu_markdown  # noqa: E402


def _minimal_eval() -> DailyOperationEval:
    return DailyOperationEval(
        overall_score=7.8,
        overall_grade="较好",
        summary_line="盈利日约 +47,261 元",
        total_daily_pnl=47261.0,
        total_asset=1_000_000.0,
        cash=50_000.0,
        order_count=4,
        cancelled_count=0,
        trade_count=5,
        positives=["分步止盈执行到位"],
        improvements=["京东方滑点偏大"],
        execution_notes=["委托 4 笔全部成交"],
        discipline_tips=["维持纪律：尾盘异常放量留意次日惯性"],
        philosophy=PhilosophyCheckResult(
            volume_zone=VolumeZone(
                label="适度参与区",
                guidance="可参与但控制仓位",
            ),
            volume_note=None,
            sector_summary="科技 2 / 制造 1",
            aligned=["低吸加仓符合交易观"],
            violations=[],
            discipline=["不追涨：买入价未贴当日高点"],
        ),
        stocks=[
            StockOpEval(
                stock_code="300502.SZ",
                stock_name="新易盛",
                daily_pnl=12000.0,
                pct_chg=4.08,
                buy_volume=100,
                sell_volume=0,
                yesterday_volume=200,
                current_volume=300,
                operation_label="顺势加仓",
                watch_note=None,
            ),
        ],
    )


def test_feishu_md_sections():
    md = build_daily_eval_feishu_markdown(
        trade_date="2026-05-22",
        synced_at="2026-05-22 14:00:00",
        account_id="test",
        health={"status": "ok"},
        account_status={"connected": True},
        orders=[
            {
                "stock_code": "300502.SZ",
                "order_type": 23,
                "order_volume": 100,
                "traded_volume": 100,
                "price": 100.0,
                "traded_price": 101.0,
                "order_status": 56,
                "order_time": 93000,
            }
        ],
        trades=[],
        name_map={"300502.SZ": "新易盛"},
        filled=1,
        cancelled=0,
        op_eval=_minimal_eval(),
    )
    assert md.startswith("# QMT Bridge 当日复盘")
    assert "## 一、统计概览" in md
    assert "## 二、当日委托" in md
    assert "## 五、当日操作评价" in md
    assert "### 交易观对照" in md
    assert "### 分标的操作" in md
    assert "daily_trade_report.py --feishu-md" in md
    assert "新易盛" in md
