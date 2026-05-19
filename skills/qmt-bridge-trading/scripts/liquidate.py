#!/usr/bin/env python3
"""清仓：按可卖数量批量卖出。默认 --dry-run 仅列出计划。

用法:
    python skills/qmt-bridge-trading/scripts/liquidate.py
    python skills/qmt-bridge-trading/scripts/liquidate.py --codes 000001.SZ,600519.SH
    python skills/qmt-bridge-trading/scripts/liquidate.py --execute --confirm
"""

from __future__ import annotations

import argparse
import json
import sys

from _common import add_client_args, call_api, load_env_files, make_client, unwrap_data

ORDER_SELL = 24


def build_liquidation_orders(
    positions: list[dict],
    *,
    codes_filter: set[str] | None,
    price_type: int,
    price: float,
    account_id: str,
    remark: str,
) -> list[dict]:
    orders: list[dict] = []
    for p in positions:
        code = p.get("stock_code") or p.get("stockCode") or ""
        if not code:
            continue
        if codes_filter and code not in codes_filter:
            continue
        vol = int(p.get("can_use_volume") or 0)
        if vol <= 0:
            continue
        orders.append(
            {
                "stock_code": code,
                "order_type": ORDER_SELL,
                "order_volume": vol,
                "price_type": price_type,
                "price": price,
                "order_remark": remark,
                "account_id": account_id,
                "strategy_name": "",
            }
        )
    return orders


def main() -> int:
    load_env_files()
    parser = argparse.ArgumentParser(description="QMT Bridge 清仓（批量卖出可卖数量）")
    add_client_args(parser)
    parser.add_argument(
        "--codes",
        default="",
        help="仅清仓指定代码，逗号分隔，如 000001.SZ,600519.SH",
    )
    parser.add_argument("--price-type", type=int, default=5, help="报价类型（默认 5 最新价）")
    parser.add_argument("--price", type=float, default=0.0, help="限价（price_type=11）")
    parser.add_argument("--remark", default="liquidate", help="委托备注")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="真实提交 batch_order",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="与 --execute 同时使用，确认实盘清仓",
    )
    args = parser.parse_args()

    # --execute 时关闭 dry-run
    dry_run = not args.execute

    if args.price_type == 11 and args.price <= 0:
        print("错误: 限价清仓须指定 --price > 0", file=sys.stderr)
        return 2

    codes_filter: set[str] | None = None
    if args.codes.strip():
        codes_filter = {c.strip() for c in args.codes.split(",") if c.strip()}

    client, account_id = make_client(args)
    positions = unwrap_data(call_api(client.query_positions, account_id=account_id))
    if not isinstance(positions, list):
        positions = []

    orders = build_liquidation_orders(
        positions,
        codes_filter=codes_filter,
        price_type=args.price_type,
        price=args.price,
        account_id=account_id,
        remark=args.remark,
    )

    if not orders:
        print("无可清仓标的（can_use_volume 均为 0 或过滤后为空）")
        return 0

    print(f"清仓计划 ({len(orders)} 笔卖出):")
    for o in orders:
        print(f"  {o['stock_code']}  volume={o['order_volume']}  price_type={o['price_type']}")

    if dry_run:
        print("\n【预览】未提交。确认后执行: .../liquidate.py --execute --confirm")
        return 0

    if not args.confirm:
        print("错误: 实盘清仓须同时指定 --execute --confirm", file=sys.stderr)
        return 2

    result = call_api(client.batch_order, orders)
    rows = unwrap_data(result)
    print("\n已提交:")
    if isinstance(rows, list):
        for row in rows:
            print(f"  {row.get('stock_code')}  order_id={row.get('order_id')}")
    else:
        print(json.dumps(result, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
