"""当日盈亏终端报告（表格输出）。"""

from __future__ import annotations

from datetime import date

from table_fmt import print_table


def _fmt_money(value: float | None, *, signed: bool = False) -> str:
    if value is None:
        return "-"
    if signed:
        return f"{value:+,.2f}"
    return f"{value:,.2f}"


def _fmt_price(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.2f}"


def _fmt_pct(last: float | None, pre: float | None) -> str:
    if last is None or pre is None or pre == 0:
        return "-"
    pct = (last - pre) / pre * 100
    return f"{pct:+.2f}%"


def _stock_name(code: str, name_map: dict[str, str]) -> str:
    return (name_map.get(code) or name_map.get(code.upper()) or "").strip() or "-"


def _source_label(source: str) -> str:
    return {"broker": "柜台", "trades": "估算", "none": "-"}.get(source, source)


def _build_stock_row(r: dict, name_map: dict[str, str], *, detail: bool) -> list[str]:
    code = r["stock_code"]
    last, pre = r.get("last_price"), r.get("pre_close")
    status = "已清仓" if r.get("cleared") else "持仓"
    mv = r.get("market_value")
    mv_s = _fmt_money(mv) if mv is not None and not r.get("cleared") else ("-" if r.get("cleared") else "-")

    base = [
        code,
        _stock_name(code, name_map),
        status,
        str(r.get("volume") or 0),
        str(r.get("yesterday_volume") or 0),
        _fmt_price(last),
        _fmt_pct(last, pre),
        mv_s,
        str(r.get("buy_volume") or 0),
        str(r.get("sell_volume") or 0),
    ]
    if detail:
        base.extend([
            _fmt_money(r.get("overnight_pnl"), signed=True),
            _fmt_money(r.get("buy_pnl"), signed=True)
            if r.get("buy_volume")
            else "-",
            _fmt_money(r.get("sell_pnl"), signed=True)
            if r.get("sell_volume")
            else "-",
        ])
    base.append(_fmt_money(r.get("daily_pnl"), signed=True))
    base.append(_source_label(r.get("daily_pnl_source", "")))
    return base


def _footer_row(
    label: str,
    rows: list[dict],
    *,
    detail: bool,
    col_count: int,
) -> list[str]:
    total_daily = sum(r.get("daily_pnl") or 0 for r in rows if r.get("daily_pnl") is not None)
    total_overnight = sum(r.get("overnight_pnl") or 0 for r in rows if r.get("overnight_pnl") is not None)
    total_buy = sum(r.get("buy_pnl") or 0 for r in rows if r.get("buy_pnl") is not None)
    total_sell = sum(r.get("sell_pnl") or 0 for r in rows if r.get("sell_pnl") is not None)

    cells = [label, "", "", "", "", "", "", "", "", ""]
    if detail:
        cells.extend([
            _fmt_money(total_overnight, signed=True),
            _fmt_money(total_buy, signed=True),
            _fmt_money(total_sell, signed=True),
        ])
    cells.append(_fmt_money(total_daily, signed=True))
    cells.append("")
    while len(cells) < col_count:
        cells.append("")
    return cells[:col_count]


def print_daily_pnl_report(
    *,
    account_id: str,
    total_asset: float,
    market_value: float,
    cash: float,
    trade_count: int,
    rows: list[dict],
    name_map: dict[str, str],
    total_daily: float,
    summary_source: str,
    show_detail: bool = True,
) -> None:
    """输出账户概览 + 个股盈亏表格。"""
    src_note = {
        "broker": "QMT 柜台",
        "trades": "持仓+成交+行情估算",
        "mixed": "混合",
        "none": "无数据",
    }.get(summary_source, summary_source)

    today = date.today().isoformat()
    width = 62

    def _box_line(text: str) -> str:
        from table_fmt import _pad_cell

        return "║" + _pad_cell(text, width, "left") + "║"

    print()
    print("╔" + "═" * width + "╗")
    print(_box_line(f"  QMT Bridge 当日盈亏报告    {today}"))
    if account_id:
        print(_box_line(f"  资金账号: {account_id}"))
    print("╚" + "═" * width + "╝")
    print()

    print("【账户概览】")
    print_table(
        ["项目", "数值", "说明"],
        [
            ["总资产", _fmt_money(total_asset), ""],
            ["持仓市值", _fmt_money(market_value), ""],
            ["可用现金", _fmt_money(cash), ""],
            ["当日成交", f"{trade_count} 笔", "query_trades"],
            ["当日盈亏合计", _fmt_money(total_daily, signed=True), src_note],
        ],
        aligns=["left", "right", "left"],
    )
    print()
    print("  估算公式: 现市值 − 昨收×昨仓 − 今日买入金额 + 今日卖出金额")
    print()

    if not rows:
        print("【个股盈亏】当日无持仓且无成交记录。")
        return

    if show_detail:
        headers = [
            "代码",
            "名称",
            "状态",
            "持仓",
            "昨仓",
            "现价",
            "涨跌幅",
            "市值",
            "买量",
            "卖量",
            "昨仓盈亏",
            "今买盈亏",
            "今卖盈亏",
            "当日盈亏",
            "来源",
        ]
        aligns = (
            ["left", "left", "center", "right", "right", "right", "right", "right",
             "right", "right", "right", "right", "right", "right", "center"]
        )
    else:
        headers = [
            "代码",
            "名称",
            "状态",
            "持仓",
            "市值",
            "买量",
            "卖量",
            "当日盈亏",
            "来源",
        ]
        aligns = ["left", "left", "center", "right", "right", "right", "right", "right", "center"]

    table_rows = [_build_stock_row(r, name_map, detail=show_detail) for r in rows]
    footer = _footer_row("合计", rows, detail=show_detail, col_count=len(headers))

    holding = [r for r in rows if not r.get("cleared")]
    cleared = [r for r in rows if r.get("cleared")]

    print(f"【个股盈亏】共 {len(rows)} 只（持仓 {len(holding)} / 已清仓 {len(cleared)}）")
    print_table(headers, table_rows, aligns=aligns, footer=footer)

    if cleared:
        print()
        print("  说明: 「已清仓」标的仅有当日卖出成交，市值栏为 -。")
