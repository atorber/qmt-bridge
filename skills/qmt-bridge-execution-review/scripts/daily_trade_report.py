#!/usr/bin/env python3
"""当日交易复盘：委托、成交、按标的汇总与操作评价（只读）。

用法:
    python skills/qmt-bridge-execution-review/scripts/daily_trade_report.py
    python skills/qmt-bridge-execution-review/scripts/daily_trade_report.py --port 8080 --api-key KEY
    python skills/qmt-bridge-execution-review/scripts/daily_trade_report.py --json
    python skills/qmt-bridge-execution-review/scripts/daily_trade_report.py --feishu-md
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
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
from execution_review_eval import (  # noqa: E402
    build_operation_evaluation,
    fetch_eval_market_context,
    format_operation_evaluation,
    operation_eval_to_dict,
)
from execution_review_feishu_md import build_daily_eval_feishu_markdown  # noqa: E402
from feishu_doc import DOC_TYPES  # noqa: E402
from orders_util import as_list, print_orders_table, summarize_by_stock  # noqa: E402
from pnl_util import (  # noqa: E402
    TradeDaySummary,
    collect_pnl_stock_codes,
    compute_daily_pnl,
    summarize_trades_by_code,
)
from stock_names import collect_stock_codes, fetch_stock_names  # noqa: E402
from trading_fmt import pick  # noqa: E402

_REPO = Path(__file__).resolve().parents[3]

_DAILY_PNL_KEYS = (
    "today_profit_loss",
    "today_close_profit_loss",
    "m_dTodayProfitLoss",
    "m_dTodayCloseProfitLoss",
)


def _broker_daily_pnl(position: dict | None) -> float | None:
    if not position:
        return None
    for k in _DAILY_PNL_KEYS:
        val = pick(position, k)
        if val is not None:
            try:
                return float(val)
            except (TypeError, ValueError):
                continue
    return None


def _fetch_pnl_breakdowns(client, account_id: str, trades: list[dict]):
    positions = unwrap_data(call_api(client.query_positions, account_id=account_id))
    if not isinstance(positions, list):
        positions = []

    trade_map = summarize_trades_by_code(trades)
    pos_by_code: dict[str, dict] = {}
    for p in positions:
        if not isinstance(p, dict):
            continue
        code = str(pick(p, "stock_code", "m_strStockCode", default="") or "").strip()
        if code:
            pos_by_code[code] = p

    codes = collect_pnl_stock_codes(positions, trade_map)
    tick_map: dict[str, dict] = {}
    if codes:
        raw = call_api(client.get_full_tick, codes)
        data = raw.get("data", raw) if isinstance(raw, dict) else {}
        if isinstance(data, dict):
            tick_map = data

    breakdowns = []
    for code in codes:
        pos = pos_by_code.get(code)
        trade = trade_map.get(code, TradeDaySummary())
        tick = tick_map.get(code) or tick_map.get(code.upper()) or {}
        breakdowns.append(
            compute_daily_pnl(
                code,
                position=pos,
                trade=trade,
                tick=tick,
                broker_daily=_broker_daily_pnl(pos),
                allow_tick=True,
            )
        )
    return breakdowns, tick_map


def main() -> int:
    load_env_files()
    parser = argparse.ArgumentParser(description="QMT Bridge 当日交易复盘（只读）")
    add_client_args(parser)
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument("--no-trades", action="store_true", help="跳过成交列表")
    parser.add_argument("--no-summary", action="store_true", help="跳过按标的汇总")
    parser.add_argument(
        "--no-eval",
        action="store_true",
        help="不输出当日操作评价",
    )
    parser.add_argument(
        "--market-turnover-yi",
        type=float,
        default=None,
        metavar="YI",
        help="两市成交额（亿元），用于交易观量能分区评价",
    )
    parser.add_argument(
        "--no-philosophy-fetch",
        action="store_true",
        help="不拉取指数/近3日涨幅（仅用当日 tick 评价）",
    )
    parser.add_argument(
        "--feishu-md",
        nargs="?",
        const=DOC_TYPES["daily-eval"].local_md,
        metavar="PATH",
        help="导出飞书 Markdown 全文（默认 reports/feishu_daily_eval.md）",
    )
    args = parser.parse_args()

    client, account_id = make_client(args)

    health = call_api(client.health_check)
    acct = unwrap_data(call_api(client.get_account_status, account_id=account_id))
    asset = unwrap_data(call_api(client.query_asset, account_id=account_id))
    if not isinstance(asset, dict):
        asset = {}

    orders = as_list(
        unwrap_data(call_api(client.query_orders, account_id=account_id))
    )
    trades = as_list(
        unwrap_data(call_api(client.query_trades, account_id=account_id))
    )

    filled = sum(
        1 for o in orders
        if int(pick(o, "traded_volume", "m_nTradedVolume", default=0) or 0) > 0
    )
    cancelled = sum(
        1 for o in orders
        if int(pick(o, "order_status", "m_nOrderStatus", default=0) or 0) == 54
    )

    codes = collect_stock_codes(orders, trades)
    name_map = fetch_stock_names(client, codes)

    op_eval = None
    breakdowns = []
    if not args.no_eval:
        breakdowns, tick_map = _fetch_pnl_breakdowns(client, account_id, trades)
        eval_codes = [b.stock_code for b in breakdowns if b.stock_code]
        cum3: dict[str, float | None] = {}
        index_avg: float | None = None
        if not args.no_philosophy_fetch:
            _, cum3, index_avg = fetch_eval_market_context(client, eval_codes)
        op_eval = build_operation_evaluation(
            orders=orders,
            trades=trades,
            breakdowns=breakdowns,
            asset=asset,
            name_map=name_map,
            cancelled_count=cancelled,
            market_turnover_yi=args.market_turnover_yi,
            cumulative_3d_pct=cum3,
            index_avg_pct=index_avg,
            tick_map=tick_map,
        )

    if args.feishu_md:
        out = Path(args.feishu_md)
        if not out.is_absolute():
            out = _REPO / out
        synced = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        trade_date = date.today().isoformat()
        md = build_daily_eval_feishu_markdown(
            trade_date=trade_date,
            synced_at=synced,
            account_id=account_id,
            health=health,
            account_status=acct,
            orders=orders,
            trades=trades,
            name_map=name_map,
            filled=filled,
            cancelled=cancelled,
            op_eval=op_eval,
            include_trades=not args.no_trades,
            include_summary=not args.no_summary,
        )
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md, encoding="utf-8")
        print(f"已写入飞书 Markdown: {out}", file=sys.stderr)

    if args.json:
        payload = {
            "date": date.today().isoformat(),
            "health": health,
            "account_status": acct,
            "account_id": account_id,
            "asset": asset,
            "stock_names": name_map,
            "orders": orders,
            "trades": trades,
            "stats": {
                "order_count": len(orders),
                "filled_count": filled,
                "cancelled_count": cancelled,
                "trade_count": len(trades),
            },
            "operation_evaluation": None
            if op_eval is None
            else operation_eval_to_dict(op_eval),
        }
        print(json.dumps(payload, ensure_ascii=False, default=str))
        return 0

    print("=== QMT Bridge 当日交易复盘 ===")
    print(f"日期: {date.today().isoformat()}")
    print(f"health: {health.get('status', health)}")
    print(f"account_status: {acct}")
    if account_id:
        print(f"account_id: {account_id}")
    print(
        f"统计: 委托 {len(orders)} 笔 | 有成交 {filled} | 已撤 {cancelled} | "
        f"成交记录 {len(trades)} 条"
    )

    print_orders_table(orders, title="当日委托", name_map=name_map)

    if not args.no_trades and trades:
        from stock_names import label_stock
        from trading_fmt import format_order_time

        print(f"--- 当日成交 ({len(trades)}) ---")
        for t in sorted(
            trades,
            key=lambda x: pick(
                x, "traded_time", "m_nTradedTime", "trade_time", default=0
            ),
        ):
            code = pick(t, "stock_code", "m_strStockCode", default="?")
            sym = label_stock(code, name_map)
            vol = int(
                pick(t, "traded_volume", "m_nTradedVolume", "trade_volume", default=0)
                or 0
            )
            price = float(
                pick(t, "traded_price", "m_dTradedPrice", "trade_price", default=0) or 0
            )
            tm = format_order_time(
                pick(t, "traded_time", "m_nTradedTime", "trade_time")
            )
            print(f"  {tm}  {sym}  {vol}@{price:.2f}")

    if not args.no_summary:
        summarize_by_stock(orders, trades, name_map=name_map)

    if op_eval is not None:
        print(format_operation_evaluation(op_eval))

    return 0


if __name__ == "__main__":
    sys.exit(main())
