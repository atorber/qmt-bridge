"""当日盈亏计算：结合持仓、昨仓与当日成交。"""

from __future__ import annotations

from dataclasses import dataclass, field

from trading_fmt import order_side, pick


@dataclass
class TradeDaySummary:
    """单标的当日成交汇总。"""

    buy_volume: int = 0
    sell_volume: int = 0
    buy_amount: float = 0.0
    sell_amount: float = 0.0

    @property
    def buy_avg(self) -> float | None:
        if self.buy_volume <= 0:
            return None
        return self.buy_amount / self.buy_volume

    @property
    def sell_avg(self) -> float | None:
        if self.sell_volume <= 0:
            return None
        return self.sell_amount / self.sell_volume

    @property
    def has_trades(self) -> bool:
        return self.buy_volume > 0 or self.sell_volume > 0


@dataclass
class DailyPnlBreakdown:
    stock_code: str
    current_volume: int
    yesterday_volume: int
    last_price: float | None
    pre_close: float | None
    daily_pnl: float | None
    overnight_pnl: float | None
    buy_pnl: float | None
    sell_pnl: float | None
    trade_summary: TradeDaySummary = field(default_factory=TradeDaySummary)
    source: str = "none"
    broker_daily_pnl: float | None = None


def summarize_trades_by_code(trades: list[dict]) -> dict[str, TradeDaySummary]:
    """按标的汇总当日买入/卖出数量与金额。"""
    out: dict[str, TradeDaySummary] = {}
    for t in trades:
        if not isinstance(t, dict):
            continue
        code = str(pick(t, "stock_code", "m_strStockCode", default="") or "").strip()
        if not code:
            continue
        side = order_side(pick(t, "order_type", "m_nOrderType"))
        vol = int(pick(t, "traded_volume", "m_nTradedVolume", "trade_volume", default=0) or 0)
        if vol <= 0:
            continue
        price = float(
            pick(t, "traded_price", "m_dTradedPrice", "trade_price", default=0) or 0
        )
        amount = pick(t, "traded_amount", "m_dTradedAmount", "trade_amount")
        amt = float(amount) if amount is not None else price * vol

        row = out.setdefault(code, TradeDaySummary())
        if side == "买入":
            row.buy_volume += vol
            row.buy_amount += amt
        elif side == "卖出":
            row.sell_volume += vol
            row.sell_amount += amt
    return out


def _to_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def tick_prices(tick: dict) -> tuple[float | None, float | None]:
    """返回 (最新价, 昨收)。"""
    if not isinstance(tick, dict):
        return None, None
    last = _to_float(pick(tick, "lastPrice", "last", "last_price"))
    pre = _to_float(
        pick(tick, "lastClose", "preClose", "pre_close", "settlementPrice")
    )
    return last, pre


def yesterday_volume_from_position(position: dict | None, trade: TradeDaySummary) -> int:
    """昨仓：优先持仓字段，否则 现仓 - 今买 + 今卖。"""
    if position:
        y = pick(
            position,
            "yesterday_volume",
            "m_nYesterdayVolume",
            "yesterdayVolume",
        )
        if y is not None:
            try:
                return max(0, int(y))
            except (TypeError, ValueError):
                pass
        vol = int(pick(position, "volume", "m_nVolume", default=0) or 0)
    else:
        vol = 0
    inferred = vol - trade.buy_volume + trade.sell_volume
    return max(0, inferred)


def compute_daily_pnl(
    code: str,
    *,
    position: dict | None,
    trade: TradeDaySummary,
    tick: dict | None,
    broker_daily: float | None = None,
    allow_tick: bool = True,
) -> DailyPnlBreakdown:
    """计算单标的当日盈亏及拆解（昨仓/今买/今卖）。"""
    vol = 0
    if position:
        vol = int(pick(position, "volume", "m_nVolume", default=0) or 0)

    y0 = yesterday_volume_from_position(position, trade)
    last, pre = tick_prices(tick or {})

    if broker_daily is not None:
        return DailyPnlBreakdown(
            stock_code=code,
            current_volume=vol,
            yesterday_volume=y0,
            last_price=last,
            pre_close=pre,
            daily_pnl=broker_daily,
            overnight_pnl=None,
            buy_pnl=None,
            sell_pnl=None,
            trade_summary=trade,
            source="broker",
            broker_daily_pnl=broker_daily,
        )

    if not allow_tick or last is None or pre is None or pre == 0:
        return DailyPnlBreakdown(
            stock_code=code,
            current_volume=vol,
            yesterday_volume=y0,
            last_price=last,
            pre_close=pre,
            daily_pnl=None,
            overnight_pnl=None,
            buy_pnl=None,
            sell_pnl=None,
            trade_summary=trade,
            source="none",
        )

    overnight = y0 * (last - pre)
    buy_part = trade.buy_volume * last - trade.buy_amount
    sell_part = trade.sell_amount - trade.sell_volume * last
    daily = vol * last - y0 * pre - trade.buy_amount + trade.sell_amount

    return DailyPnlBreakdown(
        stock_code=code,
        current_volume=vol,
        yesterday_volume=y0,
        last_price=last,
        pre_close=pre,
        daily_pnl=round(daily, 2),
        overnight_pnl=round(overnight, 2),
        buy_pnl=round(buy_part, 2) if trade.buy_volume else None,
        sell_pnl=round(sell_part, 2) if trade.sell_volume else None,
        trade_summary=trade,
        source="trades",
    )


def collect_pnl_stock_codes(
    positions: list[dict],
    trade_map: dict[str, TradeDaySummary],
) -> list[str]:
    """持仓 + 当日有成交的标的（含已清仓）。"""
    seen: set[str] = set()
    codes: list[str] = []
    for p in positions:
        if not isinstance(p, dict):
            continue
        code = str(pick(p, "stock_code", "m_strStockCode", default="") or "").strip()
        if not code or code in seen:
            continue
        vol = int(pick(p, "volume", "m_nVolume", default=0) or 0)
        if vol > 0 or trade_map.get(code, TradeDaySummary()).has_trades:
            seen.add(code)
            codes.append(code)
    for code, summary in trade_map.items():
        if code not in seen and summary.has_trades:
            seen.add(code)
            codes.append(code)
    return codes
