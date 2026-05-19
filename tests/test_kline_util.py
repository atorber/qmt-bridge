"""kline_util 单元测试（无需 Bridge）。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "_shared"))

from kline_util import (  # noqa: E402
    analyze_stock,
    cumulative_returns_pct,
    parse_daily_bars,
    pattern_next_up_probability_adaptive,
)


def _bars_from_closes(
    closes: list[float],
    *,
    volumes: list[float] | None = None,
) -> list[dict]:
    rows = []
    for i, c in enumerate(closes, 1):
        row = {"date": f"202501{i:02d}", "close": c, "open": c}
        if volumes is not None:
            row["volume"] = volumes[i - 1]
        rows.append(row)
    return rows


def test_cumulative_returns():
    bars = parse_daily_bars(_bars_from_closes([10, 10, 11, 12]))
    cum = cumulative_returns_pct(bars)
    assert cum[1] == 9.09
    assert cum[2] == 20.0


def test_analyze_stock_pattern():
    closes = [10 + (i % 3) - 1 for i in range(40)]
    analysis = analyze_stock("000001.SZ", _bars_from_closes(closes))
    assert analysis.error is None
    assert analysis.cumulative_pct[1] is not None
    assert len(analysis.recent_10) <= 10


def test_pattern_adaptive_finds_shorter():
    # 明显交替，9 日精确样本少，缩短后应能匹配
    closes = [100 + (5 if i % 2 == 0 else -5) for i in range(60)]
    bars = parse_daily_bars(_bars_from_closes(closes))
    pat = pattern_next_up_probability_adaptive(bars, pattern_len=9, min_samples=3)
    assert pat.effective_len >= 3
    assert pat.match_mode in ("exact", "short", "relaxed", "blend", "insufficient", "none")


def test_volume_probability_with_volumes():
    closes = [10.0 + i * 0.1 for i in range(50)]
    vols = [1000 + i * 50 for i in range(50)]
    analysis = analyze_stock(
        "000001.SZ",
        _bars_from_closes(closes, volumes=vols),
    )
    assert analysis.error is None
    assert analysis.volume_prob.volume_state_signature
    assert analysis.recent_10[0].get("vol_ratio") is not None
