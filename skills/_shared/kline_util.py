"""日 K 线解析、累计涨幅、形态与量价涨跌概率统计。"""

from __future__ import annotations

from dataclasses import dataclass, field

# 累计涨幅周期（交易日）
DEFAULT_CUM_PERIODS = (1, 2, 3, 4, 5, 10, 30)

# 形态匹配：首选长度与最短降级长度
DEFAULT_PATTERN_LEN = 9
MIN_PATTERN_LEN = 3
DEFAULT_MIN_PATTERN_SAMPLES = 3


@dataclass
class DailyBar:
    date: str
    close: float
    open: float | None = None
    volume: float | None = None

    @property
    def label(self) -> str:
        return self.date


@dataclass
class PatternMatchResult:
    """形态条件概率（含样本不足时的降级匹配）。"""

    probability: float | None = None
    sample_count: int = 0
    signature: str = ""
    requested_len: int = DEFAULT_PATTERN_LEN
    effective_len: int = 0
    match_mode: str = ""  # exact | short | relaxed | none


@dataclass
class VolumeProbResult:
    """量价结合的涨跌概率指标。"""

    # 收涨且放量(相对5日均量)后，下一日收涨比例
    prob_up_after_up_high_vol: float | None = None
    sample_up_high_vol: int = 0
    # 近 3 日成交量连增后，下一日收涨比例
    prob_up_after_vol_rising_3d: float | None = None
    sample_vol_rising_3d: int = 0
    # 当前「涨跌+量能」三元组形态（近 3 日）下的下一日收涨比例
    prob_up_volume_state: float | None = None
    sample_volume_state: int = 0
    volume_state_signature: str = ""
    # 近 10 日：收涨日中放量占比（量能确认度）
    up_days_volume_confirmed_pct: float | None = None


@dataclass
class ReturnAnalysis:
    stock_code: str
    bars: list[DailyBar] = field(default_factory=list)
    cumulative_pct: dict[int, float | None] = field(default_factory=dict)
    last_close: float | None = None
    recent_10: list[dict] = field(default_factory=list)
    prob_recent_10_up: float | None = None
    prob_baseline_up: float | None = None
    prob_next_up_pattern: float | None = None
    pattern_sample_count: int = 0
    pattern_signature: str = ""
    pattern_effective_len: int = 0
    pattern_match_mode: str = ""
    volume_prob: VolumeProbResult = field(default_factory=VolumeProbResult)
    error: str | None = None


def _bar_date(row: dict) -> str:
    for key in ("date", "time", "index", "datetime"):
        if key in row and row[key] is not None:
            raw = str(row[key]).strip()
            if raw.isdigit() and len(raw) >= 8:
                return raw[:8]
            if raw.isdigit() and len(raw) < 8:
                # xt 有时为毫秒时间戳
                try:
                    ts = int(raw)
                    if ts > 1_000_000_000_000:
                        from datetime import datetime

                        return datetime.utcfromtimestamp(ts / 1000).strftime("%Y%m%d")
                    if ts > 1_000_000_000:
                        from datetime import datetime

                        return datetime.utcfromtimestamp(ts).strftime("%Y%m%d")
                except (OSError, OverflowError, ValueError):
                    pass
            return raw.split()[0].replace("-", "")[:8]
    return ""


def _bar_float(row: dict, *keys: str) -> float | None:
    for key in keys:
        if key in row and row[key] is not None:
            try:
                return float(row[key])
            except (TypeError, ValueError):
                continue
    return None


def records_to_list(data) -> list[dict]:
    """将 API 返回的 list[dict] 或 DataFrame 转为记录列表。"""
    if data is None:
        return []
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    try:
        import pandas as pd

        if isinstance(data, pd.DataFrame):
            if data.empty:
                return []
            return data.reset_index().to_dict(orient="records")
    except ImportError:
        pass
    return []


def parse_daily_bars(records: list[dict]) -> list[DailyBar]:
    """将 market_data_ex 记录转为按日期升序的日 K 列表。"""
    bars: list[DailyBar] = []
    for row in records:
        if not isinstance(row, dict):
            continue
        close = _bar_float(row, "close", "Close", "settelementPrice")
        if close is None or close <= 0:
            continue
        dt = _bar_date(row)
        if not dt:
            continue
        op = _bar_float(row, "open", "Open")
        vol = _bar_float(row, "volume", "Volume", "vol", "amount")
        bars.append(DailyBar(date=dt, close=close, open=op, volume=vol))
    bars.sort(key=lambda b: b.date)
    dedup: dict[str, DailyBar] = {}
    for b in bars:
        dedup[b.date] = b
    return [dedup[k] for k in sorted(dedup)]


def cumulative_returns_pct(
    bars: list[DailyBar],
    periods: tuple[int, ...] = DEFAULT_CUM_PERIODS,
) -> dict[int, float | None]:
    """N 日累计涨幅（%）：close[-1]/close[-1-N]-1。"""
    if not bars:
        return {p: None for p in periods}
    closes = [b.close for b in bars]
    last = closes[-1]
    out: dict[int, float | None] = {}
    for n in periods:
        if len(closes) <= n:
            out[n] = None
            continue
        base = closes[-1 - n]
        if base <= 0:
            out[n] = None
        else:
            out[n] = round((last / base - 1) * 100, 2)
    return out


def _daily_returns(bars: list[DailyBar]) -> list[float]:
    rets: list[float] = []
    for i in range(1, len(bars)):
        prev, cur = bars[i - 1].close, bars[i].close
        if prev > 0:
            rets.append(cur / prev - 1)
    return rets


def _sign_pattern(rets: list[float], start: int, end: int) -> tuple[int, ...]:
    seg = rets[start:end]
    return tuple(1 if r > 0 else (-1 if r < 0 else 0) for r in seg)


def _pattern_signature(pattern: tuple[int, ...]) -> str:
    return "".join("↑" if s > 0 else ("↓" if s < 0 else "—") for s in pattern)


def _pattern_distance(a: tuple[int, ...], b: tuple[int, ...]) -> int:
    if len(a) != len(b):
        return 999
    return sum(1 for x, y in zip(a, b) if x != y)


def _collect_pattern_hits(
    rets: list[float],
    target: tuple[int, ...],
    *,
    max_mismatch: int = 0,
) -> list[bool]:
    """历史中与 target 匹配（允许 max_mismatch 位不同）的窗口，收集下一日是否收涨。"""
    plen = len(target)
    hits: list[bool] = []
    for i in range(plen, len(rets) - 1):
        cand = _sign_pattern(rets, i - plen, i)
        if _pattern_distance(cand, target) <= max_mismatch:
            hits.append(rets[i] > 0)
    return hits


def pattern_next_up_probability(
    bars: list[DailyBar],
    *,
    pattern_len: int = DEFAULT_PATTERN_LEN,
    min_samples: int = DEFAULT_MIN_PATTERN_SAMPLES,
) -> tuple[float | None, int, str]:
    """固定长度的形态条件概率（不含降级）。"""
    rets = _daily_returns(bars)
    if len(rets) < pattern_len + 2:
        return None, 0, ""

    target = _sign_pattern(rets, len(rets) - pattern_len, len(rets))
    sig = _pattern_signature(target)
    hits = _collect_pattern_hits(rets, target, max_mismatch=0)
    if len(hits) < min_samples:
        return None, len(hits), sig
    return round(sum(hits) / len(hits) * 100, 1), len(hits), sig


def pattern_next_up_probability_adaptive(
    bars: list[DailyBar],
    *,
    pattern_len: int = DEFAULT_PATTERN_LEN,
    min_pattern_len: int = MIN_PATTERN_LEN,
    min_samples: int = DEFAULT_MIN_PATTERN_SAMPLES,
) -> PatternMatchResult:
    """样本不足时自动缩短形态或放宽 1 位不匹配，尽量给出可解释的概率。"""
    result = PatternMatchResult(requested_len=pattern_len)
    rets = _daily_returns(bars)
    if len(rets) < min_pattern_len + 2:
        result.match_mode = "none"
        return result

    # 1) 精确匹配：从 pattern_len 逐步缩短到 min_pattern_len
    for plen in range(pattern_len, min_pattern_len - 1, -1):
        if len(rets) < plen + 2:
            continue
        target = _sign_pattern(rets, len(rets) - plen, len(rets))
        hits = _collect_pattern_hits(rets, target, max_mismatch=0)
        if len(hits) >= min_samples:
            result.probability = round(sum(hits) / len(hits) * 100, 1)
            result.sample_count = len(hits)
            result.signature = _pattern_signature(target)
            result.effective_len = plen
            result.match_mode = "exact" if plen == pattern_len else "short"
            return result
        # 记录最佳（样本最多）的精确匹配候选
        if len(hits) > result.sample_count:
            result.sample_count = len(hits)
            result.signature = _pattern_signature(target)
            result.effective_len = plen

    # 2) 放宽 1 位：用首选或已记录的有效长度
    try_len = result.effective_len or pattern_len
    if try_len >= min_pattern_len and len(rets) >= try_len + 2:
        target = _sign_pattern(rets, len(rets) - try_len, len(rets))
        hits = _collect_pattern_hits(rets, target, max_mismatch=1)
        if len(hits) >= min_samples:
            result.probability = round(sum(hits) / len(hits) * 100, 1)
            result.sample_count = len(hits)
            result.signature = _pattern_signature(target)
            result.effective_len = try_len
            result.match_mode = "relaxed"
            return result
        if len(hits) > result.sample_count:
            result.sample_count = len(hits)
            result.signature = _pattern_signature(target)
            result.effective_len = try_len

    # 3) 仍不足：用放宽匹配 + 向历史基准收缩的估计
    if result.sample_count > 0 and result.effective_len >= min_pattern_len:
        target = _sign_pattern(
            rets, len(rets) - result.effective_len, len(rets)
        )
        hits = _collect_pattern_hits(rets, target, max_mismatch=1)
        if not hits:
            hits = _collect_pattern_hits(rets, target, max_mismatch=0)
        if hits and len(rets) >= 5:
            baseline = sum(1 for r in rets[:-1] if r > 0) / max(len(rets) - 1, 1)
            raw_rate = sum(hits) / len(hits)
            weight = len(hits) / (len(hits) + min_samples)
            blended = weight * raw_rate + (1 - weight) * baseline
            result.probability = round(blended * 100, 1)
            result.match_mode = "blend"
            return result

    result.match_mode = "none" if result.sample_count == 0 else "insufficient"
    return result


def _volume_series(bars: list[DailyBar]) -> list[float | None]:
    return [b.volume for b in bars]


def _volume_ma(vols: list[float | None], end_idx: int, window: int = 5) -> float | None:
    """end_idx 为 bars 下标，用其前 window 日（不含当日）均量。"""
    if end_idx < window:
        return None
    seg = [v for v in vols[end_idx - window : end_idx] if v is not None and v > 0]
    if len(seg) < max(2, window // 2):
        return None
    return sum(seg) / len(seg)


def _vol_ratio(vols: list[float | None], idx: int, window: int = 5) -> float | None:
    v = vols[idx]
    if v is None or v <= 0:
        return None
    ma = _volume_ma(vols, idx, window)
    if ma is None or ma <= 0:
        return None
    return v / ma


def _vol_trend_label(vols: list[float | None], end_idx: int, days: int = 3) -> str:
    """连续 days 日成交量变化：增 / 减 / 平 / 混。"""
    if end_idx < days:
        return "?"
    seg = [vols[end_idx - days + 1 + i] for i in range(days)]
    if any(v is None or v <= 0 for v in seg):
        return "?"
    diffs = [seg[i] - seg[i - 1] for i in range(1, len(seg))]
    if all(d > 0 for d in diffs):
        return "增"
    if all(d < 0 for d in diffs):
        return "减"
    if all(d == 0 for d in diffs):
        return "平"
    return "混"


def _price_vol_state(
    rets: list[float],
    vols: list[float | None],
    bar_i: int,
    *,
    state_days: int = 3,
    vol_window: int = 5,
    high_ratio: float = 1.15,
) -> str:
    """近 state_days 日量价状态签名，如 ↑放量|↓缩量。bar_i 为窗口最后一根 K 线下标。"""
    if bar_i < state_days:
        return ""
    parts: list[str] = []
    for offset in range(state_days):
        bi = bar_i - state_days + 1 + offset
        ret_i = bi - 1
        if ret_i < 0 or ret_i >= len(rets):
            return ""
        sign = "↑" if rets[ret_i] > 0 else ("↓" if rets[ret_i] < 0 else "—")
        ratio = _vol_ratio(vols, bi, vol_window)
        if ratio is None:
            vol_tag = "?"
        elif ratio >= high_ratio:
            vol_tag = "放量"
        elif ratio <= 1 / high_ratio:
            vol_tag = "缩量"
        else:
            vol_tag = "平量"
        parts.append(f"{sign}{vol_tag}")
    return "|".join(parts)


def analyze_volume_probability(
    bars: list[DailyBar],
    *,
    min_samples: int = 5,
    vol_window: int = 5,
    state_days: int = 3,
    high_ratio: float = 1.15,
) -> VolumeProbResult:
    """量价结合的涨跌概率。"""
    out = VolumeProbResult()
    vols = _volume_series(bars)
    if not any(v is not None and v > 0 for v in vols):
        return out

    rets = _daily_returns(bars)
    n = len(bars)
    if len(rets) < vol_window + state_days + 2:
        return out

    # A) 收涨且放量日 → 下一日收涨
    hits_a: list[bool] = []
    for bar_i in range(vol_window + 1, n - 1):
        ret_i = bar_i - 1
        if ret_i < 0 or ret_i >= len(rets):
            continue
        if rets[ret_i] <= 0:
            continue
        ratio = _vol_ratio(vols, bar_i, vol_window)
        if ratio is None or ratio < high_ratio:
            continue
        next_ret = rets[ret_i + 1] if ret_i + 1 < len(rets) else None
        if next_ret is not None:
            hits_a.append(next_ret > 0)

    if len(hits_a) >= min_samples:
        out.prob_up_after_up_high_vol = round(sum(hits_a) / len(hits_a) * 100, 1)
    out.sample_up_high_vol = len(hits_a)

    # B) 3 日成交量连增 → 下一日收涨
    hits_b: list[bool] = []
    for bar_i in range(state_days + vol_window, n - 1):
        if _vol_trend_label(vols, bar_i, state_days) != "增":
            continue
        ret_i = bar_i - 1
        if ret_i + 1 < len(rets):
            hits_b.append(rets[ret_i + 1] > 0)
    if len(hits_b) >= min_samples:
        out.prob_up_after_vol_rising_3d = round(sum(hits_b) / len(hits_b) * 100, 1)
    out.sample_vol_rising_3d = len(hits_b)

    # C) 当前量价状态（近 state_days）匹配历史
    target_state = _price_vol_state(
        rets,
        vols,
        n - 1,
        state_days=state_days,
        vol_window=vol_window,
        high_ratio=high_ratio,
    )
    out.volume_state_signature = target_state
    if target_state:
        hits_c: list[bool] = []
        for bar_i in range(state_days + vol_window, n - 1):
            state = _price_vol_state(
                rets, vols, bar_i, state_days=state_days, vol_window=vol_window, high_ratio=high_ratio
            )
            if state != target_state:
                continue
            ret_i = bar_i - 1
            if ret_i + 1 < len(rets):
                hits_c.append(rets[ret_i + 1] > 0)
        out.sample_volume_state = len(hits_c)
        if len(hits_c) >= min_samples:
            out.prob_up_volume_state = round(sum(hits_c) / len(hits_c) * 100, 1)
        elif len(hits_c) > 0 and len(rets) >= 5:
            baseline = sum(1 for r in rets[:-1] if r > 0) / max(len(rets) - 1, 1)
            raw_rate = sum(hits_c) / len(hits_c)
            weight = len(hits_c) / (len(hits_c) + min_samples)
            out.prob_up_volume_state = round(
                (weight * raw_rate + (1 - weight) * baseline) * 100, 1
            )

    # D) 近 10 日收涨日中放量占比
    tail_start = max(1, n - 10)
    up_days = 0
    confirmed = 0
    for bar_i in range(tail_start, n):
        ret_i = bar_i - 1
        if ret_i < 0 or ret_i >= len(rets) or rets[ret_i] <= 0:
            continue
        up_days += 1
        ratio = _vol_ratio(vols, bar_i, vol_window)
        if ratio is not None and ratio >= high_ratio:
            confirmed += 1
    if up_days > 0:
        out.up_days_volume_confirmed_pct = round(confirmed / up_days * 100, 1)

    return out


def analyze_stock(
    code: str,
    records: list[dict],
    *,
    cum_periods: tuple[int, ...] = DEFAULT_CUM_PERIODS,
    prob_pattern_len: int = DEFAULT_PATTERN_LEN,
    min_pattern_samples: int = DEFAULT_MIN_PATTERN_SAMPLES,
) -> ReturnAnalysis:
    """单标的日 K 分析。"""
    result = ReturnAnalysis(stock_code=code)
    bars = parse_daily_bars(records)
    if len(bars) < 2:
        result.error = "日 K 不足（需至少 2 根）"
        return result

    result.bars = bars
    result.last_close = bars[-1].close
    result.cumulative_pct = cumulative_returns_pct(bars, cum_periods)

    rets = _daily_returns(bars)
    vols = _volume_series(bars)
    tail_rets = rets[-10:]
    result.recent_10 = []
    base_k = len(rets) - len(tail_rets)
    for i, r in enumerate(tail_rets):
        b = bars[base_k + i + 1]
        bar_i = base_k + i + 1
        vr = _vol_ratio(vols, bar_i)
        row = {
            "date": b.date,
            "close": round(b.close, 2),
            "return_pct": round(r * 100, 2),
            "direction": "涨" if r > 0 else ("跌" if r < 0 else "平"),
        }
        if b.volume is not None:
            row["volume"] = int(b.volume) if b.volume == int(b.volume) else round(b.volume, 0)
        if vr is not None:
            row["vol_ratio"] = round(vr, 2)
            row["vol_tag"] = "放量" if vr >= 1.15 else ("缩量" if vr <= 0.87 else "平量")
        result.recent_10.append(row)

    if tail_rets:
        result.prob_recent_10_up = round(
            sum(1 for r in tail_rets if r > 0) / len(tail_rets) * 100, 1
        )

    if len(rets) >= 5:
        result.prob_baseline_up = round(
            sum(1 for r in rets[:-1] if r > 0) / max(len(rets) - 1, 1) * 100, 1
        )

    pat = pattern_next_up_probability_adaptive(
        bars,
        pattern_len=prob_pattern_len,
        min_samples=min_pattern_samples,
    )
    result.prob_next_up_pattern = pat.probability
    result.pattern_sample_count = pat.sample_count
    result.pattern_signature = pat.signature
    result.pattern_effective_len = pat.effective_len
    result.pattern_match_mode = pat.match_mode

    result.volume_prob = analyze_volume_probability(bars)
    return result
