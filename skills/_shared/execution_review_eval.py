"""当日交易操作评价：结合委托/成交、盈亏拆解与执行质量。"""

from __future__ import annotations

from dataclasses import dataclass, field

from orders_util import slippage_bps
from pnl_util import DailyPnlBreakdown, TradeDaySummary
from trading_fmt import order_side, pick
from trading_philosophy import (
    IntradayRange,
    PhilosophyCheckResult,
    SLIPPAGE_SEVERE_BP,
    apply_trading_philosophy,
    buy_position_in_range,
    classify_buy_timing,
    intraday_from_tick,
)


@dataclass
class StockOpEval:
    stock_code: str
    stock_name: str
    daily_pnl: float | None = None
    pct_chg: float | None = None
    buy_volume: int = 0
    sell_volume: int = 0
    yesterday_volume: int = 0
    current_volume: int = 0
    operation_label: str = ""
    watch_note: str = ""
    buy_avg: float | None = None
    range_position: float | None = None
    intraday: IntradayRange | None = None


@dataclass
class DailyOperationEval:
    total_daily_pnl: float | None = None
    total_asset: float | None = None
    cash: float | None = None
    order_count: int = 0
    cancelled_count: int = 0
    trade_count: int = 0
    overall_score: float = 0.0
    overall_grade: str = ""
    summary_line: str = ""
    positives: list[str] = field(default_factory=list)
    improvements: list[str] = field(default_factory=list)
    execution_notes: list[str] = field(default_factory=list)
    discipline_tips: list[str] = field(default_factory=list)
    philosophy: PhilosophyCheckResult | None = None
    stocks: list[StockOpEval] = field(default_factory=list)


def fetch_eval_market_context(
    client,
    stock_codes: list[str],
) -> tuple[float | None, dict[str, float | None], float | None]:
    """拉取评价用上下文：指数均涨跌幅、各标的近 3 日累计涨幅（%）。成交额需外部传入。"""
    from kline_util import cumulative_returns_pct, parse_daily_bars, records_to_list

    index_avg: float | None = None
    try:
        raw_idx = client.get_major_indices()
        if isinstance(raw_idx, dict):
            tick_map = raw_idx.get("data") or {}
            codes = raw_idx.get("indices") or []
            pcts: list[float] = []
            for code in codes:
                t = tick_map.get(code) or tick_map.get(str(code).upper()) or {}
                if not isinstance(t, dict):
                    continue
                last = float(t.get("lastPrice") or t.get("lastClose") or 0)
                prev = float(t.get("lastClose") or t.get("preClose") or 0)
                if prev:
                    pcts.append((last - prev) / prev * 100)
            if pcts:
                index_avg = round(sum(pcts) / len(pcts), 2)
    except Exception:
        pass

    cum3: dict[str, float | None] = {}
    for code in stock_codes:
        if not code:
            continue
        try:
            raw = client.get_history_ex(
                stocks=[code],
                period="1d",
                count=6,
                dividend_type="front",
            )
            data = raw.get("data", raw) if isinstance(raw, dict) else {}
            recs = []
            if isinstance(data, dict):
                recs = data.get(code) or data.get(code.upper()) or []
            bars = parse_daily_bars(records_to_list(recs))
            cum = cumulative_returns_pct(bars, (3,))
            cum3[code] = cum.get(3)
        except Exception:
            cum3[code] = None
    return None, cum3, index_avg


def _pct_chg(b: DailyPnlBreakdown) -> float | None:
    if b.last_price is None or b.pre_close is None or b.pre_close == 0:
        return None
    return round((b.last_price / b.pre_close - 1) * 100, 2)


def _classify_operation(
    b: DailyPnlBreakdown,
    pct: float | None,
    day: IntradayRange | None = None,
) -> tuple[str, str]:
    t = b.trade_summary
    if not t.has_trades:
        return "持股未交易", "无主动调仓"

    if t.sell_volume > 0 and t.buy_volume == 0:
        if pct is not None and pct >= 3:
            return "大涨止盈", "逢高减仓兑现"
        if pct is not None and pct <= -1:
            return "弱势减仓", "下跌中卖出"
        return "减仓", "卖出为主"

    if t.buy_volume > 0 and t.sell_volume == 0:
        label, note, _ = classify_buy_timing(
            t.buy_avg, day, pct_chg=pct
        )
        return label, note

    return "买卖调仓", "同日有买有卖"


def _analyze_orders(orders: list[dict], name_map: dict[str, str]) -> list[str]:
    notes: list[str] = []
    bad_slips: list[str] = []
    for o in orders:
        if not isinstance(o, dict):
            continue
        traded = int(pick(o, "traded_volume", "m_nTradedVolume", default=0) or 0)
        if traded <= 0:
            continue
        price = float(pick(o, "price", "m_dPrice", default=0) or 0)
        tprice = float(pick(o, "traded_price", "m_dTradedPrice", default=0) or 0)
        side = order_side(pick(o, "order_type", "m_nOrderType"))
        code = pick(o, "stock_code", "m_strStockCode", default="")
        bps = slippage_bps(price, tprice, side)
        if bps is not None and abs(bps) >= 30:
            sym = name_map.get(code, code)
            bad_slips.append(f"{sym} {side} {bps:+.1f}bp")
            if abs(bps) >= SLIPPAGE_SEVERE_BP:
                bad_slips[-1] += " [严重]"

    if bad_slips:
        notes.append("滑点偏大：" + "；".join(bad_slips))
    return notes


def build_operation_evaluation(
    *,
    orders: list[dict],
    trades: list[dict],
    breakdowns: list[DailyPnlBreakdown],
    asset: dict | None,
    name_map: dict[str, str],
    cancelled_count: int,
    market_turnover_yi: float | None = None,
    cumulative_3d_pct: dict[str, float | None] | None = None,
    index_avg_pct: float | None = None,
    tick_map: dict[str, dict] | None = None,
) -> DailyOperationEval:
    """生成当日操作评价（统计归纳，非投资建议）。"""
    result = DailyOperationEval(
        order_count=len(orders),
        cancelled_count=cancelled_count,
        trade_count=len(trades),
    )

    if isinstance(asset, dict):
        result.total_asset = _to_float(
            pick(asset, "total_asset", "m_dTotalAsset")
        )
        result.cash = _to_float(pick(asset, "cash", "m_dCash"))

    total_pnl = 0.0
    has_pnl = False
    for b in breakdowns:
        if b.daily_pnl is not None:
            total_pnl += b.daily_pnl
            has_pnl = True
    if has_pnl:
        result.total_daily_pnl = round(total_pnl, 2)

    ticks = tick_map or {}
    for b in breakdowns:
        code = b.stock_code
        pct = _pct_chg(b)
        tick = ticks.get(code) or ticks.get(code.upper()) or {}
        day = intraday_from_tick(tick if isinstance(tick, dict) else None)
        label, watch = _classify_operation(b, pct, day)
        buy_avg = b.trade_summary.buy_avg
        range_pos = (
            buy_position_in_range(buy_avg, day) if buy_avg is not None else None
        )
        result.stocks.append(
            StockOpEval(
                stock_code=code,
                stock_name=name_map.get(code, ""),
                daily_pnl=b.daily_pnl,
                pct_chg=pct,
                buy_volume=b.trade_summary.buy_volume,
                sell_volume=b.trade_summary.sell_volume,
                yesterday_volume=b.yesterday_volume,
                current_volume=b.current_volume,
                operation_label=label,
                watch_note=watch,
                buy_avg=buy_avg,
                range_position=range_pos,
                intraday=day,
            )
        )

    result.stocks.sort(
        key=lambda s: (s.daily_pnl is None, -(s.daily_pnl or 0)),
    )

    # 做得好的
    for s in result.stocks:
        if s.daily_pnl is not None and s.daily_pnl > 5000 and s.sell_volume > s.buy_volume:
            result.positives.append(
                f"{_sym(s)}：{_fmt_pnl(s.daily_pnl)}，{s.operation_label}（卖{s.sell_volume}/买{s.buy_volume}）"
            )
        elif s.daily_pnl is not None and s.daily_pnl > 3000 and s.operation_label in (
            "顺势加仓",
            "低吸加仓",
        ):
            result.positives.append(
                f"{_sym(s)}：{_fmt_pnl(s.daily_pnl)}，{s.operation_label}"
            )

    # 需改进（仅对有主动交易的标的）
    for s in result.stocks:
        traded = s.buy_volume > 0 or s.sell_volume > 0
        if not traded:
            if s.daily_pnl is not None and s.daily_pnl > 5000 and (s.pct_chg or 0) >= 3:
                result.positives.append(
                    f"{_sym(s)}：{_fmt_pnl(s.daily_pnl)}（{s.pct_chg:+.2f}%），持股浮盈未调仓"
                )
            continue
        if s.daily_pnl is not None and s.daily_pnl < -2000:
            result.improvements.append(
                f"{_sym(s)}：当日{_fmt_pnl(s.daily_pnl)}，{s.operation_label} — {s.watch_note}"
            )
        elif s.operation_label == "逆势加仓" and s.buy_volume >= 200:
            result.improvements.append(
                f"{_sym(s)}：逆势加仓 {s.buy_volume} 股（昨{s.yesterday_volume}→今{s.current_volume}），{s.watch_note}"
            )

    if cancelled_count > 0:
        result.execution_notes.append(
            f"委托 {cancelled_count} 笔已撤，建议减少频繁改价撤单"
        )
    result.execution_notes.extend(_analyze_orders(orders, name_map))

    if result.cash is not None and result.total_asset and result.total_asset > 0:
        cash_pct = result.cash / result.total_asset * 100
        if cash_pct < 2:
            result.execution_notes.append(
                f"可用现金占比仅 {cash_pct:.1f}%，调仓弹性偏低"
            )

    score = 7.0
    if result.total_daily_pnl is not None:
        if result.total_daily_pnl > 0:
            score += 1.0
        else:
            score -= 1.5
    neg_ops = sum(1 for s in result.stocks if s.daily_pnl is not None and s.daily_pnl < 0 and s.buy_volume > 0)
    if neg_ops >= 2:
        score -= 0.5
    if len(result.positives) >= 2:
        score += 0.5
    if any("滑点偏大" in n for n in result.execution_notes):
        score -= 0.5
    if cancelled_count >= 3:
        score -= 0.3

    buy_avg_by_code = {
        s.stock_code: s.buy_avg for s in result.stocks if s.buy_avg is not None
    }
    intraday_by_code = {
        s.stock_code: s.intraday
        for s in result.stocks
        if s.intraday is not None
    }
    result.philosophy = apply_trading_philosophy(
        stocks=result.stocks,
        name_map=name_map,
        total_asset=result.total_asset,
        cash=result.cash,
        order_count=result.order_count,
        cancelled_count=cancelled_count,
        market_turnover_yi=market_turnover_yi,
        cumulative_3d_pct=cumulative_3d_pct,
        index_avg_pct=index_avg_pct,
        execution_notes=result.execution_notes,
        buy_avg_by_code=buy_avg_by_code,
        intraday_by_code=intraday_by_code,
    )
    phil = result.philosophy
    if phil.violations:
        score -= min(1.5, 0.35 * len(phil.violations))
    if phil.aligned:
        score += min(0.8, 0.2 * len(phil.aligned))
    if phil.volume_zone and phil.volume_zone.label == "谨慎区" and any(
        s.buy_volume > s.sell_volume for s in result.stocks
    ):
        score -= 0.4

    score = max(1.0, min(10.0, round(score, 1)))
    result.overall_score = score
    result.overall_grade = _grade(score)

    if result.total_daily_pnl is not None and result.total_daily_pnl >= 0:
        result.summary_line = (
            f"盈利日约 {_fmt_pnl(result.total_daily_pnl)}，"
            f"主动交易以{'止盈减仓' if any('止盈' in s.operation_label for s in result.stocks) else '调仓'}为主"
        )
    else:
        result.summary_line = "当日合计亏损，宜复盘买卖节奏与仓位纪律"

    result.discipline_tips = _discipline_tips(result, phil)
    return result


def _discipline_tips(
    ev: DailyOperationEval,
    phil: PhilosophyCheckResult | None = None,
) -> list[str]:
    tips: list[str] = []
    if phil and phil.volume_note:
        tips.append(f"量能：{phil.volume_note}")
    for s in ev.stocks:
        if s.operation_label == "逆势加仓":
            tips.append(f"{_sym(s)}：停止盲目摊薄，放量企稳再加仓")
        elif s.operation_label == "大涨止盈" and s.current_volume > 0:
            tips.append(f"{_sym(s)}：余仓移动止盈，勿因卖飞追高买回")
        elif s.operation_label == "顺势加仓":
            tips.append(f"{_sym(s)}：加仓单以今日买入均价为防守参考")
    if ev.cash is not None and ev.total_asset and ev.cash / ev.total_asset < 0.05:
        tips.append("账户：下次止盈可多留现金，保留调仓弹性")
    if not tips:
        tips.append("维持纪律：盘中以昨高/昨低为界，尾盘异常放量留意次日惯性")
    return tips


def _grade(score: float) -> str:
    if score >= 8:
        return "较好"
    if score >= 6:
        return "中等"
    return "待改进"


def _sym(s: StockOpEval) -> str:
    return f"{s.stock_code} {s.stock_name}".strip()


def _fmt_pnl(v: float) -> str:
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:,.0f} 元"


def _philosophy_to_dict(p: PhilosophyCheckResult | None) -> dict | None:
    if p is None:
        return None
    return {
        "volume_zone": p.volume_zone.label if p.volume_zone else None,
        "volume_note": p.volume_note,
        "sector_summary": p.sector_summary,
        "aligned": p.aligned,
        "violations": p.violations,
        "discipline": p.discipline,
    }


def _to_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def format_operation_evaluation(ev: DailyOperationEval) -> str:
    lines = [
        "",
        "=" * 60,
        "【当日操作评价】（统计归纳，非投资建议；对照交易观）",
        "=" * 60,
        f"总评 {ev.overall_score}/10（{ev.overall_grade}） · {ev.summary_line}",
    ]
    if ev.total_daily_pnl is not None:
        lines.append(f"当日盈亏合计（估算）：{_fmt_pnl(ev.total_daily_pnl)}")
    lines.append(
        f"委托 {ev.order_count} 笔 · 已撤 {ev.cancelled_count} · 成交 {ev.trade_count} 条"
    )

    if ev.philosophy:
        p = ev.philosophy
        lines.append("\n▸ 交易观对照")
        if p.sector_summary:
            lines.append(f"  · {p.sector_summary}")
        if p.volume_zone:
            lines.append(f"  · 量能分区：{p.volume_zone.label} — {p.volume_zone.guidance}")
        elif p.volume_note:
            lines.append(f"  · {p.volume_note}")
        for a in p.aligned:
            lines.append(f"  · ✓ {a}")

    if ev.positives:
        lines.append("\n▸ 做得好的")
        for p in ev.positives:
            lines.append(f"  · {p}")

    if ev.philosophy and ev.philosophy.violations:
        lines.append("\n▸ 戒律检查（需改进）")
        for v in ev.philosophy.violations:
            lines.append(f"  · {v}")

    if ev.improvements:
        lines.append("\n▸ 需改进")
        for p in ev.improvements:
            lines.append(f"  · {p}")

    if ev.execution_notes:
        lines.append("\n▸ 执行质量")
        for p in ev.execution_notes:
            lines.append(f"  · {p}")

    if ev.philosophy and ev.philosophy.discipline:
        lines.append("\n▸ 纪律提示（交易观）")
        for d in ev.philosophy.discipline:
            lines.append(f"  · {d}")

    if ev.stocks:
        lines.append("\n▸ 分标的操作")
        for s in ev.stocks:
            pnl_s = _fmt_pnl(s.daily_pnl) if s.daily_pnl is not None else "—"
            pct_s = f"{s.pct_chg:+.2f}%" if s.pct_chg is not None else "—"
            lines.append(
                f"  · {_sym(s)}：{pnl_s}（{pct_s}）| {s.operation_label} | "
                f"买{s.buy_volume}/卖{s.sell_volume} | 仓 {s.yesterday_volume}→{s.current_volume}"
            )

    if ev.discipline_tips:
        lines.append("\n▸ 明日纪律提示")
        for t in ev.discipline_tips:
            lines.append(f"  · {t}")
    lines.append("")
    return "\n".join(lines)


def operation_eval_to_dict(ev: DailyOperationEval) -> dict:
    return {
        "overall_score": ev.overall_score,
        "overall_grade": ev.overall_grade,
        "summary_line": ev.summary_line,
        "total_daily_pnl": ev.total_daily_pnl,
        "total_asset": ev.total_asset,
        "cash": ev.cash,
        "order_count": ev.order_count,
        "cancelled_count": ev.cancelled_count,
        "trade_count": ev.trade_count,
        "positives": ev.positives,
        "improvements": ev.improvements,
        "execution_notes": ev.execution_notes,
        "discipline_tips": ev.discipline_tips,
        "philosophy": _philosophy_to_dict(ev.philosophy),
        "stocks": [
            {
                "stock_code": s.stock_code,
                "stock_name": s.stock_name,
                "daily_pnl": s.daily_pnl,
                "pct_chg": s.pct_chg,
                "buy_volume": s.buy_volume,
                "sell_volume": s.sell_volume,
                "yesterday_volume": s.yesterday_volume,
                "current_volume": s.current_volume,
                "operation_label": s.operation_label,
                "watch_note": s.watch_note,
            }
            for s in ev.stocks
        ],
    }
