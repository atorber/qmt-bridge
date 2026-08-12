"""交易观标准：板块归类、量能分区、评价阈值（供 execution_review_eval 使用）。"""

from __future__ import annotations

from dataclasses import dataclass, field

# --- 量能（亿元，两市成交额，由调用方传入或 --market-turnover-yi）---
TURNOVER_CAUTIOUS_MAX_YI = 10_000.0  # <1万亿
TURNOVER_MODERATE_MAX_YI = 28_500.0  # 1～2.85万亿；≥2.85万亿才算高热区

# --- 止盈 / 低吸 / 追涨 ---
TAKE_PROFIT_1D_PCT = 5.0  # 单日涨幅偏离大 → 宜分步止盈
TAKE_PROFIT_3D_PCT = 8.0  # 近 3 交易日累计涨幅 → 宜分步止盈
# 追涨/低吸：以**买入均价在当日振幅中的位置**为准，不用收盘涨跌幅
# 位置 0≈当日低点、1≈当日高点；(high-low) 无效时回退昨收/开盘价启发式
CHASE_RANGE_POSITION = 0.65  # 买入价处于振幅上段 → 追涨
DIP_RANGE_POSITION = 0.40  # 买入价处于振幅下段 → 低吸
# 买均价明显低于收盘价：说明买在拉升前/中低位，收盘大涨仍属低吸成功
DIP_UPLIFT_FROM_BUY_PCT = 2.0  # (收盘-买均)/买均 ≥ 此值 → 偏低吸
CHASE_NEAR_CLOSE_RATIO = 0.995  # 买均 ≥ 收盘×此比例 → 贴近尾盘追高
DIP_BUY_PCT = -2.0  # 无振幅数据时：收盘大跌净买入
STRONG_RISE_HOLD_PCT = 3.0  # 温和上涨未卖 → 可考虑分步止盈（非戒律）
SUCCESS_DIP_CLOSE_PCT = 5.0  # 收盘大涨 + 低吸 → 正向「低吸成功」

# --- 组合聚焦 ---
MAX_HOLDINGS_FOCUS = 6  # 超过提示做减法
MAX_ACTIVE_TRADED_TODAY = 4  # 当日成交标的过多
MIN_CASH_PCT_CAUTIOUS = 15.0
MIN_CASH_PCT_MODERATE = 10.0

# --- 执行 ---
SLIPPAGE_WARN_BP = 30.0
SLIPPAGE_SEVERE_BP = 100.0
ORDER_COUNT_BUSY = 10
CANCEL_COUNT_BUSY = 3

SECTORS = ("大金融", "消费", "周期", "科技")


@dataclass
class IntradayRange:
    """当日价格区间（来自 full_tick 或日 K）。"""

    low: float | None = None
    high: float | None = None
    open: float | None = None
    pre_close: float | None = None
    last: float | None = None


def intraday_from_tick(tick: dict | None) -> IntradayRange:
    """从 full_tick 解析当日高低开。"""
    if not tick or not isinstance(tick, dict):
        return IntradayRange()

    def _f(*keys: str) -> float | None:
        for k in keys:
            v = tick.get(k)
            if v is not None:
                try:
                    return float(v)
                except (TypeError, ValueError):
                    continue
        return None

    return IntradayRange(
        low=_f("low", "Low", "m_dLow"),
        high=_f("high", "High", "m_dHigh"),
        open=_f("open", "Open", "m_dOpen"),
        pre_close=_f("lastClose", "preClose", "m_dPreClose", "pre_close"),
        last=_f("lastPrice", "last", "m_dLast"),
    )


def buy_position_in_range(buy_avg: float, day: IntradayRange) -> float | None:
    """买入价在当日振幅中的相对位置，0=贴近低点，1=贴近高点。"""
    if day.low is None or day.high is None:
        return None
    span = day.high - day.low
    if span <= 0:
        return None
    pos = (buy_avg - day.low) / span
    return max(0.0, min(1.0, pos))


def uplift_from_buy_pct(buy_avg: float, day: IntradayRange) -> float | None:
    """买均至收盘（现价）的上行幅度 %，越大说明买在拉升前越多。"""
    last = day.last
    if last is None or buy_avg <= 0 or last <= buy_avg:
        return None
    return (last - buy_avg) / buy_avg * 100


def classify_buy_timing(
    buy_avg: float | None,
    day: IntradayRange | None,
    pct_chg: float | None = None,
) -> tuple[str, str, float | None]:
    """判定买入相对当日价格的位置（按买均，不按收盘涨跌幅）。

    返回 (标签, 说明, 振幅位置 0~1 或 None)。
    """
    if buy_avg is None or buy_avg <= 0:
        return "加仓", "买入为主", None

    day = day or IntradayRange()
    pos = buy_position_in_range(buy_avg, day)
    uplift = uplift_from_buy_pct(buy_avg, day)
    last = day.last

    # 贴近尾盘/当日高价买入 → 追涨
    if last and buy_avg >= last * CHASE_NEAR_CLOSE_RATIO:
        return "追涨加仓", f"买入均价 {buy_avg:.2f} 贴近收盘价 {last:.2f}，忌追涨", pos
    if pos is not None and pos >= CHASE_RANGE_POSITION:
        return "追涨加仓", f"买入价处于当日高价区（振幅位置约 {pos * 100:.0f}%），忌追涨", pos

    # 买在后段仍明显低于收盘 → 低吸（含「买后大涨」）
    if uplift is not None and uplift >= DIP_UPLIFT_FROM_BUY_PCT:
        note = f"买均 {buy_avg:.2f}，收盘较买均上行约 +{uplift:.1f}%"
        if pct_chg is not None and pct_chg >= SUCCESS_DIP_CLOSE_PCT:
            return "低吸加仓", f"{note}，收盘大涨属低吸成功", pos
        return "低吸加仓", note, pos

    if pos is not None:
        pct_s = f"{pos * 100:.0f}%"
        if pos <= DIP_RANGE_POSITION:
            return "低吸加仓", f"买入价贴近当日低价区（振幅位置约 {pct_s}）", pos
        return "顺势加仓", f"买入价处于当日振幅中部（约 {pct_s}）", pos

    # 无 high/low：用昨收粗判
    ref = day.pre_close or day.open
    if ref and ref > 0:
        rel = (buy_avg - ref) / ref * 100
        if rel <= 0.5:
            return "低吸加仓", f"买入均价较昨收仅 {rel:+.2f}%（无分时高低时用昨收参照）", None
        if rel >= 2.5 and (uplift is None or uplift < DIP_UPLIFT_FROM_BUY_PCT):
            return "追涨加仓", f"买入均价较昨收 {rel:+.2f}% 偏高（无分时高低时用昨收参照）", None
    if pct_chg is not None and pct_chg <= DIP_BUY_PCT:
        return "逆势加仓", "下跌日买入，注意止损纪律", None
    return "加仓", "买入为主（缺少当日高低价，无法判断追涨/低吸）", None


def is_chase_rise_buy_by_price(
    buy_avg: float | None,
    day: IntradayRange | None,
) -> bool:
    """是否视为追涨买入（按买入价，不看收盘涨幅）。"""
    if buy_avg is None:
        return False
    label, _, _ = classify_buy_timing(buy_avg, day)
    return label == "追涨加仓"


@dataclass
class VolumeZone:
    label: str
    guidance: str


@dataclass
class TurnoverDay:
    """单日两市成交额（亿元）及量能分区。"""

    trade_date: str  # YYYYMMDD
    turnover_yi: float
    zone_label: str = ""


# 近 N 日量能环比阈值（%）
HEAT_TREND_UP_PCT = 5.0
HEAT_TREND_DOWN_PCT = -8.0
HEAT_SPIKE_PULLBACK_PCT = -10.0  # 相对近段峰值回落


@dataclass
class PhilosophyCheckResult:
    """交易观对照检查结果。"""

    volume_zone: VolumeZone | None = None
    volume_note: str = ""
    market_turnover_yi: float | None = None
    turnover_history: list[TurnoverDay] = field(default_factory=list)
    market_heat_label: str = ""
    market_heat_summary: str = ""
    sector_summary: str = ""
    aligned: list[str] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)
    discipline: list[str] = field(default_factory=list)


def classify_sector(stock_code: str, stock_name: str = "") -> str:
    """按代码/名称粗分四板块（启发式，供复盘聚焦用）。"""
    code = (stock_code or "").upper()
    name = stock_name or ""

    finance_kw = ("银行", "证券", "保险", "信托", "券商", "期货")
    consume_kw = ("白酒", "食品", "饮料", "家电", "零售", "医药", "中药", "创新药")
    cycle_kw = ("钢铁", "煤炭", "有色", "稀土", "黄金", "化工", "石油", "矿业", "能源", "水泥")
    tech_kw = ("科技", "半导体", "芯片", "通信", "软件", "电子", "光学", "算力", "人工智能")

    for kw in finance_kw:
        if kw in name:
            return "大金融"
    for kw in consume_kw:
        if kw in name:
            return "消费"
    for kw in cycle_kw:
        if kw in name:
            return "周期"
    for kw in tech_kw:
        if kw in name:
            return "科技"

    if code.startswith("688") or code.startswith("300") or code.startswith("301"):
        return "科技"
    if code.startswith(("600036", "601318", "601166", "600030", "601688")):
        return "大金融"
    if code.startswith(("600519", "000858", "603288")):
        return "消费"
    # 封测/存储/面板等默认归科技赛道
    if code.startswith(("600584", "603986", "688008", "300394", "300502", "000725")):
        return "科技"
    return "科技"


def classify_volume_zone(turnover_yi: float | None) -> VolumeZone | None:
    """两市成交额（亿元）→ 量能分区。"""
    if turnover_yi is None or turnover_yi <= 0:
        return None
    if turnover_yi < TURNOVER_CAUTIOUS_MAX_YI:
        return VolumeZone(
            label="谨慎区",
            guidance=f"成交额约 {turnover_yi:,.0f} 亿（<1万亿）：宜减仓位、慎加仓",
        )
    if turnover_yi < TURNOVER_MODERATE_MAX_YI:
        return VolumeZone(
            label="适度参与区",
            guidance=f"成交额约 {turnover_yi:,.0f} 亿（1～2.85万亿）：结构性行情，控制仓位",
        )
    return VolumeZone(
        label="≥2.85万亿区",
        guidance=f"成交额约 {turnover_yi:,.0f} 亿（≥2.85万亿）：高热区，可积极但须观察能否持续",
    )


def format_turnover_history_line(days: list[TurnoverDay]) -> str:
    """近 N 日两市成交额一行摘要。"""
    if not days:
        return ""
    parts = []
    for d in days:
        md = d.trade_date[4:6] + "-" + d.trade_date[6:8] if len(d.trade_date) >= 8 else d.trade_date
        parts.append(f"{md} {d.turnover_yi:,.0f}亿({d.zone_label})")
    return "近{}日两市：".format(len(days)) + " → ".join(parts)


def assess_market_heat(
    history: list[TurnoverDay],
    *,
    today_yi: float | None = None,
) -> tuple[str, str, list[str], list[str], list[TurnoverDay]]:
    """根据连续多日成交额评估市场热度。

    返回 (热度标签, 一行摘要, 符合项补充, 戒律/风险提示补充, 整理后的日序列)。
    """
    from datetime import date as _date

    days = sorted(list(history), key=lambda d: d.trade_date)
    if today_yi is not None and today_yi > 0:
        today_key = _date.today().strftime("%Y%m%d")
        zone = classify_volume_zone(today_yi)
        zl = zone.label if zone else "—"
        if days and days[-1].trade_date == today_key:
            days[-1] = TurnoverDay(today_key, today_yi, zl)
        else:
            days.append(TurnoverDay(today_key, today_yi, zl))
    days = days[-3:]
    if len(days) < 2:
        return (
            "数据不足",
            "近3日成交额历史不足（本地日缓存缺少历史交易日；请连续收盘复盘累积，或 QMT 正常后运行 backfill --try-history）",
            [],
            [],
            days,
        )

    summary = format_turnover_history_line(days)
    aligned: list[str] = []
    alerts: list[str] = []

    active_n = sum(1 for d in days if d.turnover_yi >= TURNOVER_MODERATE_MAX_YI)
    cautious_n = sum(1 for d in days if d.turnover_yi < TURNOVER_CAUTIOUS_MAX_YI)
    latest = days[-1]
    prev = days[-2]
    chg_1d = (
        (latest.turnover_yi - prev.turnover_yi) / prev.turnover_yi * 100
        if prev.turnover_yi > 0
        else 0.0
    )
    chg_span = (
        (latest.turnover_yi - days[0].turnover_yi) / days[0].turnover_yi * 100
        if days[0].turnover_yi > 0
        else 0.0
    )
    peak = max(days, key=lambda d: d.turnover_yi)
    pullback = 0.0
    if peak.turnover_yi > 0 and latest.trade_date != peak.trade_date:
        pullback = (latest.turnover_yi - peak.turnover_yi) / peak.turnover_yi * 100

    monotonic_up = all(
        days[i].turnover_yi < days[i + 1].turnover_yi for i in range(len(days) - 1)
    )
    monotonic_down = all(
        days[i].turnover_yi > days[i + 1].turnover_yi for i in range(len(days) - 1)
    )

    heat = "温和"
    if active_n >= len(days) and len(days) >= 3:
        heat = "持续高热"
        aligned.append("近3日两市均≥2.85万亿，量能维持高位，市场热度偏强")
    elif active_n >= 2 and (monotonic_up or chg_span >= HEAT_TREND_UP_PCT):
        heat = "热度升温"
        aligned.append(
            f"量能升温：最新 {latest.turnover_yi:,.0f} 亿，较近3日前 +{chg_span:.1f}%"
        )
    elif cautious_n >= 2:
        heat = "市场偏冷"
        alerts.append("近3日多数低于1万亿，市场热度偏弱，宜控仓慎追")
    elif monotonic_down or chg_span <= HEAT_TREND_DOWN_PCT:
        heat = "热度降温"
        alerts.append(
            f"量能降温：最新 {latest.turnover_yi:,.0f} 亿，较近3日前 {chg_span:+.1f}%"
        )
    elif (
        len(days) >= 3
        and peak.turnover_yi >= TURNOVER_MODERATE_MAX_YI
        and pullback <= HEAT_SPIKE_PULLBACK_PCT
        and latest.trade_date != peak.trade_date
    ):
        heat = "放量回落"
        alerts.append(
            f"成交额自峰值 {peak.turnover_yi:,.0f} 亿（{peak.trade_date[4:8]}）回落 {pullback:.1f}%，警惕短线过热衰减"
        )
    elif latest.turnover_yi >= TURNOVER_MODERATE_MAX_YI and chg_1d <= HEAT_TREND_DOWN_PCT:
        heat = "高位缩量"
        alerts.append(
            f"较前日缩量 {chg_1d:+.1f}%（{prev.turnover_yi:,.0f}→{latest.turnover_yi:,.0f} 亿），高位宜谨慎"
        )
    elif latest.turnover_yi >= TURNOVER_MODERATE_MAX_YI:
        heat = "高位活跃"
        aligned.append(f"当日成交额 {latest.turnover_yi:,.0f} 亿处于活跃区，关注能否连续维持")
    elif latest.turnover_yi < TURNOVER_CAUTIOUS_MAX_YI:
        heat = "偏低活跃"
        alerts.append(f"当日成交额 {latest.turnover_yi:,.0f} 亿 <1万亿，以防守与精选为主")

    detail = (
        f"{summary}；热度「{heat}」"
        f"（较前日 {chg_1d:+.1f}%"
        + (f"，较近3日前 {chg_span:+.1f}%" if len(days) >= 3 else "")
        + "）"
    )
    return heat, detail, aligned, alerts, days


def apply_trading_philosophy(
    *,
    stocks: list,  # StockOpEval-like: pct_chg, buy_volume, sell_volume, operation_label, ...
    name_map: dict[str, str],
    total_asset: float | None,
    cash: float | None,
    order_count: int,
    cancelled_count: int,
    market_turnover_yi: float | None = None,
    turnover_history: list[TurnoverDay] | None = None,
    cumulative_3d_pct: dict[str, float | None] | None = None,
    index_avg_pct: float | None = None,
    execution_notes: list[str] | None = None,
    buy_avg_by_code: dict[str, float | None] | None = None,
    intraday_by_code: dict[str, IntradayRange] | None = None,
) -> PhilosophyCheckResult:
    """根据交易观生成对照与戒律检查。"""
    out = PhilosophyCheckResult()
    execution_notes = execution_notes or []

    out.market_turnover_yi = market_turnover_yi
    zone = classify_volume_zone(market_turnover_yi)
    out.volume_zone = zone
    if zone:
        out.volume_note = zone.guidance
    else:
        out.volume_note = (
            "未提供两市成交额（可用 --market-turnover-yi 传入，单位：亿元）；"
            "请人工对照：<1万亿谨慎、1～2.85万亿适度、≥2.85万亿高热且持续可积极"
        )

    heat_label, heat_summary, heat_aligned, heat_alerts, resolved_days = assess_market_heat(
        list(turnover_history or []), today_yi=market_turnover_yi
    )
    out.turnover_history = resolved_days
    out.market_heat_label = heat_label
    out.market_heat_summary = heat_summary
    out.aligned.extend(heat_aligned)
    out.violations.extend(heat_alerts)
    if heat_label not in ("数据不足", "温和") and heat_summary:
        out.discipline.append(f"市场热度：{heat_label} — 结合量能变化控制进攻节奏")

    sectors: dict[str, list[str]] = {s: [] for s in SECTORS}
    for st in stocks:
        code = getattr(st, "stock_code", "")
        nm = getattr(st, "stock_name", "") or name_map.get(code, "")
        sec = classify_sector(code, nm)
        sectors[sec].append(nm or code)
    active_secs = [k for k, v in sectors.items() if v]
    parts = [f"{k}{len(v)}只" for k, v in sectors.items() if v]
    out.sector_summary = "持仓板块：" + "、".join(parts) if parts else "持仓板块：—"
    if len(active_secs) >= 3:
        out.violations.append(
            f"板块分散（{len(active_secs)} 类）：交易观强调做减法、聚焦少数赛道"
        )

    holding_n = len(stocks)
    traded_n = sum(
        1
        for s in stocks
        if getattr(s, "buy_volume", 0) > 0 or getattr(s, "sell_volume", 0) > 0
    )
    if holding_n > MAX_HOLDINGS_FOCUS:
        out.violations.append(
            f"持仓 {holding_n} 只，超过聚焦上限 {MAX_HOLDINGS_FOCUS}，宜收缩交易股票池"
        )
    if traded_n > MAX_ACTIVE_TRADED_TODAY:
        out.violations.append(
            f"当日 {traded_n} 只有成交，分散专注度（建议 ≤{MAX_ACTIVE_TRADED_TODAY}）"
        )

    if total_asset and cash is not None and total_asset > 0:
        cash_pct = cash / total_asset * 100
        if zone and zone.label == "谨慎区" and cash_pct < MIN_CASH_PCT_CAUTIOUS:
            out.violations.append(
                f"谨慎区现金仅 {cash_pct:.1f}%（建议 ≥{MIN_CASH_PCT_CAUTIOUS:.0f}%）"
            )
        elif zone and zone.label == "适度参与区" and cash_pct < MIN_CASH_PCT_MODERATE:
            out.discipline.append(
                f"现金占比 {cash_pct:.1f}%，适度区宜保留 ≥{MIN_CASH_PCT_MODERATE:.0f}% 弹性"
            )
        elif cash_pct < 5:
            out.violations.append(f"现金占比仅 {cash_pct:.1f}%，调仓与控回撤弹性不足")

    cum3 = cumulative_3d_pct or {}
    buy_avgs = buy_avg_by_code or {}
    intradays = intraday_by_code or {}
    for st in stocks:
        code = getattr(st, "stock_code", "")
        pct = getattr(st, "pct_chg", None)
        buy_v = getattr(st, "buy_volume", 0) or 0
        sell_v = getattr(st, "sell_volume", 0) or 0
        label = getattr(st, "operation_label", "")
        sym = f"{code} {name_map.get(code, '')}".strip()
        buy_avg = buy_avgs.get(code)
        if buy_avg is None:
            buy_avg = getattr(st, "buy_avg", None)
        day = intradays.get(code) or getattr(st, "intraday", None)

        c3 = cum3.get(code)
        if c3 is not None and c3 >= TAKE_PROFIT_3D_PCT and sell_v == 0 and buy_v == 0:
            out.violations.append(
                f"{sym}：近3日累计约 +{c3:.1f}%，未分步止盈（会卖的是师傅）"
            )
        elif c3 is not None and c3 >= TAKE_PROFIT_3D_PCT and sell_v < buy_v:
            out.discipline.append(f"{sym}：近3日累计 +{c3:.1f}%，卖出偏少，宜分步止盈")

        if pct is not None and pct >= TAKE_PROFIT_1D_PCT and sell_v == 0 and buy_v == 0:
            out.violations.append(
                f"{sym}：单日 +{pct:.1f}% 未止盈，偏离度大宜分步兑现"
            )
        elif pct is not None and pct >= STRONG_RISE_HOLD_PCT and sell_v == 0 and buy_v == 0:
            out.discipline.append(
                f"{sym}：单日 +{pct:.1f}% 持股未动，浮盈可考虑分步止盈"
            )

        if buy_v > sell_v and buy_avg is not None:
            timing_label, timing_note, range_pos = classify_buy_timing(
                buy_avg, day, pct_chg=pct
            )
            if timing_label == "追涨加仓":
                out.violations.append(f"{sym}：{timing_note}")
            elif timing_label == "低吸加仓":
                if pct is not None and pct >= SUCCESS_DIP_CLOSE_PCT:
                    out.aligned.append(
                        f"{sym}：低吸成功（买均{buy_avg:.2f}），收盘+{pct:.1f}%"
                    )
                else:
                    out.aligned.append(f"{sym}：{timing_note}")
            elif timing_label == "逆势加仓":
                if buy_v >= 500:
                    out.discipline.append(
                        f"{sym}：下跌日买入 {buy_v} 股，须确认是否「大跌分步低吸」而非摊薄"
                    )
                else:
                    out.violations.append(f"{sym}：{timing_note}")
            elif label in ("顺势加仓", "加仓", "低吸加仓"):
                if range_pos is not None and range_pos <= DIP_RANGE_POSITION:
                    out.aligned.append(f"{sym}：{timing_note}")

        if index_avg_pct is not None and pct is not None and buy_v > sell_v:
            if index_avg_pct <= -0.5 and pct <= -1:
                out.violations.append(
                    f"{sym}：大盘偏弱仍加仓，宜敬畏市场、保全本金"
                )

    for note in execution_notes:
        if "滑点偏大" in note:
            out.violations.append(f"执行：{note}（交易要算账）")
        if "≥" in note and "bp" in note.lower():
            pass

    if order_count > ORDER_COUNT_BUSY:
        out.discipline.append(
            f"委托 {order_count} 笔偏多，交易须专注（对手为机器与信息优势方）"
        )
    if cancelled_count >= CANCEL_COUNT_BUSY:
        out.discipline.append(f"撤单 {cancelled_count} 笔，减少频繁改价")

    # 做得好的（交易观正向）
    for st in stocks:
        if getattr(st, "operation_label", "") == "大涨止盈":
            out.aligned.append(
                f"{getattr(st, 'stock_code', '')}：大涨分步止盈，符合会卖的是师傅"
            )
        if getattr(st, "operation_label", "") == "持股未交易":
            pnl = getattr(st, "daily_pnl", None)
            pct = getattr(st, "pct_chg", None)
            if pnl is not None and pnl > 0 and pct is not None and pct >= 2:
                out.aligned.append(
                    f"{getattr(st, 'stock_code', '')}：反弹日持股未乱动，顺势持有"
                )

    if traded_n <= 2 and order_count <= 5:
        out.aligned.append("交易克制：委托少、聚焦度高，符合操作与研究分离")

    return out
