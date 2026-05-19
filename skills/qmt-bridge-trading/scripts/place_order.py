#!/usr/bin/env python3
"""单笔委托：默认仅预览，须 --execute --confirm 才会真实下单。

用法:
    python skills/qmt-bridge-trading/scripts/place_order.py 000001.SZ --buy --volume 100
    python skills/qmt-bridge-trading/scripts/place_order.py 600519.SH --sell --volume 100 --limit 1800.0 --execute --confirm
"""

from __future__ import annotations

import argparse
import json
import sys

from _common import add_client_args, call_api, load_env_files, make_client

ORDER_BUY = 23
ORDER_SELL = 24


def main() -> int:
    load_env_files()
    parser = argparse.ArgumentParser(description="QMT Bridge 单笔下单")
    add_client_args(parser)
    parser.add_argument("stock_code", help="股票代码，如 000001.SZ")
    direction = parser.add_mutually_exclusive_group(required=True)
    direction.add_argument("--buy", action="store_true", help="买入 (order_type=23)")
    direction.add_argument("--sell", action="store_true", help="卖出 (order_type=24)")
    parser.add_argument("--volume", type=int, required=True, help="委托数量（股）")
    parser.add_argument(
        "--price-type",
        type=int,
        default=5,
        help="报价类型：5=最新价，11=限价（默认 5）",
    )
    parser.add_argument("--price", type=float, default=0.0, help="限价价格（price_type=11 时必填）")
    parser.add_argument("--remark", default="agent", help="委托备注")
    parser.add_argument("--strategy", default="", help="策略名称")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="真实提交（默认仅预览）",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="与 --execute 同时使用，确认实盘下单",
    )
    args = parser.parse_args()

    order_type = ORDER_BUY if args.buy else ORDER_SELL
    side = "买入" if args.buy else "卖出"

    if args.price_type == 11 and args.price <= 0:
        print("错误: 限价单须指定 --price > 0", file=sys.stderr)
        return 2

    if args.volume <= 0:
        print("错误: --volume 须为正整数", file=sys.stderr)
        return 2

    plan = {
        "stock_code": args.stock_code,
        "order_type": order_type,
        "side": side,
        "order_volume": args.volume,
        "price_type": args.price_type,
        "price": args.price,
        "order_remark": args.remark,
        "strategy_name": args.strategy,
    }

    if not args.execute:
        print("【预览】未提交委托。确认后请加 --execute --confirm")
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0

    if not args.confirm:
        print("错误: 实盘下单须同时指定 --execute --confirm", file=sys.stderr)
        return 2

    client, account_id = make_client(args)
    result = call_api(
        client.place_order,
        stock_code=args.stock_code,
        order_type=order_type,
        order_volume=args.volume,
        price_type=args.price_type,
        price=args.price,
        strategy_name=args.strategy,
        order_remark=args.remark,
        account_id=account_id,
    )
    order_id = result.get("order_id", result)
    print(f"已提交 {side} {args.stock_code} x{args.volume}  order_id={order_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
