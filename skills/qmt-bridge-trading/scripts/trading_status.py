#!/usr/bin/env python3
"""交易前检查：health、账户状态、持仓与资产摘要（只读）。

用法（在仓库根目录）:
    python skills/qmt-bridge-trading/scripts/trading_status.py
    python skills/qmt-bridge-trading/scripts/trading_status.py --json
"""

from __future__ import annotations

import argparse
import json
import sys

from _common import (
    add_client_args,
    call_api,
    fmt_num,
    load_env_files,
    make_client,
    unwrap_data,
)


def main() -> int:
    load_env_files()
    parser = argparse.ArgumentParser(description="QMT Bridge 交易状态摘要（只读）")
    add_client_args(parser)
    parser.add_argument("--json", action="store_true", help="输出紧凑 JSON")
    parser.add_argument("--no-positions", action="store_true", help="跳过持仓")
    parser.add_argument("--no-asset", action="store_true", help="跳过资产")
    args = parser.parse_args()

    client, account_id = make_client(args)

    health = call_api(client.health_check)
    acct_status = call_api(
        client.get_account_status,
        account_id=account_id,
    )

    positions = []
    if not args.no_positions:
        positions = unwrap_data(
            call_api(
                client.query_positions,
                account_id=account_id,
            )
        )
        if not isinstance(positions, list):
            positions = []

    asset = {}
    if not args.no_asset:
        raw_asset = unwrap_data(
            call_api(
                client.query_asset,
                account_id=account_id,
            )
        )
        if isinstance(raw_asset, dict):
            asset = raw_asset

    if args.json:
        payload = {
            "health": health,
            "account_status": acct_status,
            "positions": positions,
            "asset": asset,
            "account_id": account_id,
        }
        print(json.dumps(payload, ensure_ascii=False, default=str))
        return 0

    print("=== QMT Bridge 交易状态 ===")
    print(f"health: {health.get('status', health)}")
    if isinstance(acct_status, dict):
        status_data = unwrap_data(acct_status)
    else:
        status_data = acct_status
    print(f"account_status: {status_data}")
    if account_id:
        print(f"account_id: {account_id}")

    if not args.no_asset and asset:
        print("--- 资产 ---")
        print(
            f"  cash={fmt_num(asset.get('cash'))}  "
            f"market_value={fmt_num(asset.get('market_value'))}  "
            f"total_asset={fmt_num(asset.get('total_asset'))}"
        )

    if not args.no_positions:
        print(f"--- 持仓 ({len(positions)}) ---")
        if not positions:
            print("  (无持仓)")
        for p in positions:
            code = p.get("stock_code", "?")
            vol = p.get("volume", 0)
            usable = p.get("can_use_volume", 0)
            mkt = p.get("market_value", 0)
            print(
                f"  {code}  vol={vol}  can_use={usable}  "
                f"market_value={fmt_num(mkt)}"
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
