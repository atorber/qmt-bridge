#!/usr/bin/env python3
"""当日盈亏快照：结合持仓、昨仓与当日买卖成交（只读）。

用法:
    python skills/qmt-bridge-daily-pnl/scripts/daily_pnl_snapshot.py
    python skills/qmt-bridge-daily-pnl/scripts/daily_pnl_snapshot.py --port 8080 --api-key KEY
    python skills/qmt-bridge-daily-pnl/scripts/daily_pnl_snapshot.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[2] / "_shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from common import (  # noqa: E402
    add_client_args,
    call_api,
    load_env_files,
    make_client,
    unwrap_data,
)
from orders_util import as_list  # noqa: E402
from pnl_display import print_daily_pnl_report  # noqa: E402
from pnl_util import (  # noqa: E402
    DailyPnlBreakdown,
    TradeDaySummary,
    collect_pnl_stock_codes,
    compute_daily_pnl,
    summarize_trades_by_code,
)
from stock_names import fetch_stock_names  # noqa: E402
from trading_fmt import pick  # noqa: E402

_DAILY_PNL_KEYS = (
    "today_profit_loss",
    "today_close_profit_loss",
    "m_dTodayProfitLoss",
    "m_dTodayCloseProfitLoss",
)
_FLOAT_PNL_KEYS = (
    "float_profit",
    "position_profit",
    "m_dFloatProfit",
    "m_dPositionProfit",
)


def _to_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _pick_float(d: dict, *keys: str) -> float | None:
    return _to_float(pick(d, *keys))


def _broker_daily_pnl(position: dict | None) -> float | None:
    if not position:
        return None
    for k in _DAILY_PNL_KEYS:
        val = _pick_float(position, k)
        if val is not None:
            return val
    return None


def _breakdown_to_row(b: DailyPnlBreakdown, position: dict | None) -> dict:
    t = b.trade_summary
    return {
        "stock_code": b.stock_code,
        "volume": b.current_volume,
        "yesterday_volume": b.yesterday_volume,
        "market_value": _pick_float(position or {}, "market_value", "m_dMarketValue")
        if position
        else None,
        "daily_pnl": b.daily_pnl,
        "daily_pnl_source": b.source,
        "overnight_pnl": b.overnight_pnl,
        "buy_pnl": b.buy_pnl,
        "sell_pnl": b.sell_pnl,
        "buy_volume": t.buy_volume,
        "sell_volume": t.sell_volume,
        "buy_amount": round(t.buy_amount, 2),
        "sell_amount": round(t.sell_amount, 2),
        "last_price": b.last_price,
        "pre_close": b.pre_close,
        "float_pnl": _pick_float(position or {}, *_FLOAT_PNL_KEYS) if position else None,
        "cleared": b.current_volume == 0 and t.has_trades,
    }


def main() -> int:
    load_env_files()
    parser = argparse.ArgumentParser(
        description="QMT Bridge 当日盈亏（持仓+当日成交，只读）"
    )
    add_client_args(parser)
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument(
        "--no-tick-fallback",
        action="store_true",
        help="不使用行情估算（无 QMT 当日盈亏字段时可能无数据）",
    )
    parser.add_argument(
        "--min-pnl",
        type=float,
        default=None,
        help="仅显示绝对值不低于该金额的标的（元）",
    )
    parser.add_argument(
        "--no-detail",
        action="store_true",
        help="个股表不展示昨仓/今买/今卖盈亏列",
    )
    args = parser.parse_args()

    client, account_id = make_client(args)

    asset = unwrap_data(call_api(client.query_asset, account_id=account_id))
    if not isinstance(asset, dict):
        asset = {}

    positions = unwrap_data(call_api(client.query_positions, account_id=account_id))
    if not isinstance(positions, list):
        positions = []

    trades = as_list(
        unwrap_data(call_api(client.query_trades, account_id=account_id))
    )
    trade_map = summarize_trades_by_code(trades)

    pos_by_code: dict[str, dict] = {}
    for p in positions:
        if not isinstance(p, dict):
            continue
        code = str(pick(p, "stock_code", "m_strStockCode", default="") or "").strip()
        if code:
            pos_by_code[code] = p

    codes = collect_pnl_stock_codes(positions, trade_map)
    allow_tick = not args.no_tick_fallback

    tick_map: dict[str, dict] = {}
    if allow_tick and codes:
        raw = call_api(client.get_full_tick, codes)
        data = raw.get("data", raw) if isinstance(raw, dict) else {}
        if isinstance(data, dict):
            tick_map = data

    breakdowns: list[DailyPnlBreakdown] = []
    for code in codes:
        pos = pos_by_code.get(code)
        trade = trade_map.get(code, TradeDaySummary())
        tick = tick_map.get(code) or tick_map.get(code.upper()) or {}
        broker = _broker_daily_pnl(pos)
        breakdowns.append(
            compute_daily_pnl(
                code,
                position=pos,
                trade=trade,
                tick=tick,
                broker_daily=broker,
                allow_tick=allow_tick,
            )
        )

    rows = [_breakdown_to_row(b, pos_by_code.get(b.stock_code)) for b in breakdowns]

    if args.min_pnl is not None:
        threshold = abs(args.min_pnl)
        rows = [
            r
            for r in rows
            if r["daily_pnl"] is not None and abs(r["daily_pnl"]) >= threshold
        ]

    rows.sort(key=lambda r: (r["daily_pnl"] is None, -(r["daily_pnl"] or 0)))

    total_daily = sum(r["daily_pnl"] or 0 for r in rows if r["daily_pnl"] is not None)
    sources = {r["daily_pnl_source"] for r in rows if r.get("daily_pnl") is not None}
    if not sources:
        summary_source = "none"
    elif sources == {"broker"}:
        summary_source = "broker"
    elif sources <= {"trades"}:
        summary_source = "trades"
    else:
        summary_source = "mixed"

    name_map = fetch_stock_names(client, [r["stock_code"] for r in rows])

    cash = _pick_float(asset, "cash", "m_dCash") or 0.0
    market_value = _pick_float(asset, "market_value", "m_dMarketValue") or 0.0
    total_asset = _pick_float(asset, "total_asset", "m_dTotalAsset") or 0.0

    if args.json:
        holding_rows = [r for r in rows if not r.get("cleared")]
        cleared_rows = [r for r in rows if r.get("cleared")]
        for r in rows:
            code = r["stock_code"]
            r["stock_name"] = name_map.get(code) or name_map.get(code.upper()) or ""
        print(
            json.dumps(
                {
                    "date": date.today().isoformat(),
                    "account_id": account_id,
                    "asset": asset,
                    "trade_count": len(trades),
                    "stock_names": name_map,
                    "symbols": rows,
                    "positions": holding_rows,
                    "cleared": cleared_rows,
                    "summary": {
                        "total_daily_pnl": round(total_daily, 2) if rows else None,
                        "total_daily_pnl_source": summary_source,
                        "symbol_count": len(rows),
                        "holding_count": len(holding_rows),
                        "cleared_count": len(cleared_rows),
                    },
                },
                ensure_ascii=False,
                default=str,
            )
        )
        return 0

    print_daily_pnl_report(
        account_id=account_id,
        total_asset=total_asset,
        market_value=market_value,
        cash=cash,
        trade_count=len(trades),
        rows=rows,
        name_map=name_map,
        total_daily=total_daily,
        summary_source=summary_source,
        show_detail=not args.no_detail,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
