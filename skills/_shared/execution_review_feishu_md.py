"""当日复盘 → 飞书 Markdown 全文导出（与终端输出结构一致）。"""

from __future__ import annotations

from execution_review_eval import DailyOperationEval


def _sym(s) -> str:
    return f"{s.stock_code} {s.stock_name}".strip()


def _fmt_pnl(v: float) -> str:
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:,.0f} 元"
from feishu_doc import DOC_TYPES, format_title
from orders_util import slippage_bps
from stock_names import label_stock
from trading_fmt import format_order_time, order_side, order_status_label, pick


def _orders_table_md(orders: list[dict], name_map: dict[str, str]) -> list[str]:
    lines = [f"## 二、当日委托（{len(orders)}）", ""]
    if not orders:
        lines.append("（无）")
        return lines
    lines.append("| 时间 | 标的 | 方向 | 委托 | 成交 | 状态 | 滑点 |")
    lines.append("|------|------|------|------|------|------|------|")
    for o in sorted(orders, key=lambda x: pick(x, "order_time", "m_nOrderTime", default=0)):
        code = pick(o, "stock_code", "m_strStockCode", default="?")
        sym = label_stock(code, name_map)
        side = order_side(pick(o, "order_type", "m_nOrderType"))
        vol = int(pick(o, "order_volume", "m_nOrderVolume", default=0) or 0)
        traded = int(pick(o, "traded_volume", "m_nTradedVolume", default=0) or 0)
        price = float(pick(o, "price", "m_dPrice", default=0) or 0)
        tprice = float(pick(o, "traded_price", "m_dTradedPrice", default=0) or 0)
        status = order_status_label(pick(o, "order_status", "m_nOrderStatus"))
        t = format_order_time(pick(o, "order_time", "m_nOrderTime"))
        slip_s = "—"
        if traded > 0 and price > 0 and tprice > 0:
            bps = slippage_bps(price, tprice, side)
            if bps is not None:
                slip_s = f"{bps:+.1f}bp"
        lines.append(
            f"| {t} | {sym} | {side} | {vol}@{price:.2f} | "
            f"{traded}@{tprice:.2f} | {status} | {slip_s} |"
        )
    return lines


def _trades_md(trades: list[dict], name_map: dict[str, str]) -> list[str]:
    lines = [f"## 三、当日成交（{len(trades)}）", ""]
    if not trades:
        lines.append("（无）")
        return lines
    for t in sorted(
        trades,
        key=lambda x: pick(x, "traded_time", "m_nTradedTime", "trade_time", default=0),
    ):
        code = pick(t, "stock_code", "m_strStockCode", default="?")
        sym = label_stock(code, name_map)
        vol = int(pick(t, "traded_volume", "m_nTradedVolume", "trade_volume", default=0) or 0)
        price = float(pick(t, "traded_price", "m_dTradedPrice", "trade_price", default=0) or 0)
        tm = format_order_time(pick(t, "traded_time", "m_nTradedTime", "trade_time"))
        lines.append(f"- {tm} **{sym}** {vol}@{price:.2f}")
    return lines


def _stock_summary_md(
    orders: list[dict],
    trades: list[dict],
    name_map: dict[str, str],
) -> list[str]:
    summary: dict[str, dict[str, int]] = {}
    for o in orders:
        code = pick(o, "stock_code", "m_strStockCode", default="")
        if not code:
            continue
        side = order_side(pick(o, "order_type", "m_nOrderType"))
        traded = int(pick(o, "traded_volume", "m_nTradedVolume", default=0) or 0)
        if code not in summary:
            summary[code] = {"买入": 0, "卖出": 0}
        if traded > 0:
            summary[code][side] = summary[code].get(side, 0) + traded
    if trades:
        for t in trades:
            code = pick(t, "stock_code", "m_strStockCode", default="")
            if not code or code in summary:
                continue
            summary[code] = {"买入": 0, "卖出": 0}
    lines = ["## 四、按标的成交汇总", ""]
    if not summary:
        lines.append("（无）")
        return lines
    lines.append("| 标的 | 买入 | 卖出 | 净变动 |")
    lines.append("|------|------|------|--------|")
    for code in sorted(summary):
        b = summary[code].get("买入", 0)
        s = summary[code].get("卖出", 0)
        sym = label_stock(code, name_map)
        lines.append(f"| {sym} | {b} | {s} | {b - s} |")
    return lines


def format_operation_evaluation_md(ev: DailyOperationEval) -> str:
    """与终端 `format_operation_evaluation` 同结构，改为 Markdown 标题。"""
    lines = [
        "## 五、当日操作评价",
        "",
        "> 统计归纳，非投资建议；对照交易观（追涨/低吸按买入均价判断）。",
        "",
        f"**总评** {ev.overall_score}/10（{ev.overall_grade}） · {ev.summary_line}",
    ]
    if ev.total_daily_pnl is not None:
        lines.append(f"**当日盈亏合计（估算）**：{_fmt_pnl(ev.total_daily_pnl)}")
    lines.append(
        f"委托 {ev.order_count} 笔 · 已撤 {ev.cancelled_count} · 成交 {ev.trade_count} 条"
    )

    if ev.philosophy:
        p = ev.philosophy
        lines.extend(["", "### 交易观对照", ""])
        if p.sector_summary:
            lines.append(f"- {p.sector_summary}")
        if p.volume_zone:
            lines.append(f"- 量能分区：**{p.volume_zone.label}** — {p.volume_zone.guidance}")
        elif p.volume_note:
            lines.append(f"- {p.volume_note}")
        for a in p.aligned:
            lines.append(f"- ✓ {a}")

    if ev.positives:
        lines.extend(["", "### 做得好的", ""])
        for p in ev.positives:
            lines.append(f"- {p}")

    if ev.philosophy and ev.philosophy.violations:
        lines.extend(["", "### 戒律检查（需改进）", ""])
        for v in ev.philosophy.violations:
            lines.append(f"- {v}")

    if ev.improvements:
        lines.extend(["", "### 需改进", ""])
        for p in ev.improvements:
            lines.append(f"- {p}")

    if ev.execution_notes:
        lines.extend(["", "### 执行质量", ""])
        for p in ev.execution_notes:
            lines.append(f"- {p}")

    if ev.philosophy and ev.philosophy.discipline:
        lines.extend(["", "### 纪律提示（交易观）", ""])
        for d in ev.philosophy.discipline:
            lines.append(f"- {d}")

    if ev.stocks:
        lines.extend(["", "### 分标的操作", ""])
        lines.append("| 标的 | 当日盈亏 | 涨跌 | 操作 | 买/卖 | 仓位变化 |")
        lines.append("|------|----------|------|------|-------|----------|")
        for s in ev.stocks:
            pnl_s = _fmt_pnl(s.daily_pnl) if s.daily_pnl is not None else "—"
            pct_s = f"{s.pct_chg:+.2f}%" if s.pct_chg is not None else "—"
            lines.append(
                f"| {_sym(s)} | {pnl_s} | {pct_s} | {s.operation_label} | "
                f"买{s.buy_volume}/卖{s.sell_volume} | "
                f"{s.yesterday_volume}→{s.current_volume} |"
            )

    if ev.discipline_tips:
        lines.extend(["", "### 明日纪律提示", ""])
        for t in ev.discipline_tips:
            lines.append(f"- {t}")

    return "\n".join(lines)


def build_daily_eval_feishu_markdown(
    *,
    trade_date: str,
    synced_at: str,
    account_id: str | None,
    health: dict | str,
    account_status,
    orders: list[dict],
    trades: list[dict],
    name_map: dict[str, str],
    filled: int,
    cancelled: int,
    op_eval: DailyOperationEval | None,
    include_trades: bool = True,
    include_summary: bool = True,
) -> str:
    """生成飞书复盘 Markdown 全文（章节与终端输出一一对应）。"""
    spec = DOC_TYPES["daily-eval"]
    title = format_title(
        spec.title_prefix,
        trade_date=trade_date,
        synced_at=synced_at,
    )
    health_s = health.get("status", health) if isinstance(health, dict) else str(health)

    parts: list[str] = [
        f"# {title}",
        "",
        f"**交易日**：{trade_date}  ",
        f"**同步时间**：{synced_at}  ",
        f"**账户**：{account_id or '默认'} | health: {health_s}",
        "",
        "---",
        "",
        "## 一、统计概览",
        "",
        "| 项目 | 数值 |",
        "|------|------|",
        f"| 委托 | {len(orders)} 笔 |",
        f"| 有成交 | {filled} 笔 |",
        f"| 已撤 | {cancelled} 笔 |",
        f"| 成交记录 | {len(trades)} 条 |",
    ]
    if op_eval and op_eval.total_daily_pnl is not None:
        parts.append(f"| **当日盈亏（估算）** | **{_fmt_pnl(op_eval.total_daily_pnl)}** |")
        parts.append(f"| **总评** | **{op_eval.overall_score}/10（{op_eval.overall_grade}）** |")

    parts.extend(["", "---", ""])
    parts.extend(_orders_table_md(orders, name_map))
    parts.append("")

    if include_trades:
        parts.extend(_trades_md(trades, name_map))
        parts.append("")

    if include_summary:
        parts.extend(_stock_summary_md(orders, trades, name_map))
        parts.append("")

    if op_eval is not None:
        parts.append(format_operation_evaluation_md(op_eval))
        parts.append("")

    parts.extend(
        [
            "---",
            "",
            "*由 `daily_trade_report.py --feishu-md` 自动生成，与终端复盘结构一致。*",
        ]
    )
    return "\n".join(parts)
