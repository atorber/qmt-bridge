#!/usr/bin/env python3
"""多周期累计涨幅 + 形态/量价涨跌概率（只读）。

用法:
    just agent-return-analysis --holdings --host 127.0.0.1 --port 8080 --api-key KEY
    python skills/qmt-bridge-return-analysis/scripts/return_probability_analysis.py \\
        --codes 000001.SZ,600519.SH
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[2] / "_shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from common import (  # noqa: E402
    add_client_args,
    call_api,
    load_env_files,
    make_client,
)
from kline_util import (  # noqa: E402
    DEFAULT_CUM_PERIODS,
    ReturnAnalysis,
    analyze_stock,
    parse_daily_bars,
    records_to_list,
)
from positions_util import fetch_position_codes  # noqa: E402
from stock_names import fetch_stock_names, label_stock  # noqa: E402
from table_fmt import print_table  # noqa: E402

_DEFAULT_COUNT = 150
_DEFAULT_DOWNLOAD_START = "20240101"
_MIN_BARS = 2


def _parse_codes(raw: str) -> list[str]:
    return [c.strip() for c in raw.split(",") if c.strip()]


def _fetch_bars(client, codes: list[str], count: int, dividend_type: str) -> dict:
    raw = call_api(
        client.get_history_ex,
        codes,
        period="1d",
        count=count,
        dividend_type=dividend_type,
        fill_data=True,
    )
    return raw if isinstance(raw, dict) else {}


def _records_for_code(bar_map: dict, code: str) -> list[dict]:
    raw = bar_map.get(code)
    if raw is None:
        raw = bar_map.get(code.upper())
    return records_to_list(raw)


def _codes_without_bars(
    bar_map: dict,
    codes: list[str],
    *,
    min_bars: int = _MIN_BARS,
) -> list[str]:
    missing: list[str] = []
    for code in codes:
        if len(parse_daily_bars(_records_for_code(bar_map, code))) < min_bars:
            missing.append(code)
    return missing


def _ensure_daily_bars(
    client,
    codes: list[str],
    count: int,
    dividend_type: str,
    *,
    download_start: str,
    skip_download: bool,
) -> dict:
    """拉取日 K；缺失时触发服务端下载后重试。"""
    bar_map = _fetch_bars(client, codes, count, dividend_type)
    missing = _codes_without_bars(bar_map, codes)
    if not missing or skip_download:
        return bar_map

    print(
        f"日 K 不足，正在下载 {len(missing)} 只: {', '.join(missing)} "
        f"（{download_start} 起）…",
        file=sys.stderr,
    )
    call_api(
        client.download_batch,
        missing,
        period="1d",
        start_time=download_start,
        end_time="",
    )
    bar_map = _fetch_bars(client, codes, count, dividend_type)
    still = _codes_without_bars(bar_map, codes)
    if still:
        print(f"警告: 下载后仍无有效日 K: {', '.join(still)}", file=sys.stderr)
    return bar_map


def _resolve_codes(args, client, account_id: str) -> list[str]:
    if args.holdings:
        codes = fetch_position_codes(client, account_id)
        if not codes:
            print("错误: 当前账户无持仓", file=sys.stderr)
            sys.exit(2)
        print(f"已读取持仓 {len(codes)} 只: {', '.join(codes)}", file=sys.stderr)
        return codes
    codes = _parse_codes(args.codes or "")
    if not codes:
        print("错误: 请指定 --codes 或 --holdings", file=sys.stderr)
        sys.exit(2)
    return codes


def _fmt_pct(v: float | None) -> str:
    if v is None:
        return "-"
    return f"{v:+.2f}%"


def _fmt_prob(v: float | None) -> str:
    if v is None:
        return "-"
    return f"{v:.1f}%"


def _pattern_mode_label(mode: str) -> str:
    return {
        "exact": "精确9日",
        "short": "缩短形态",
        "relaxed": "放宽1位",
        "blend": "小样本收缩",
        "insufficient": "样本仍不足",
        "none": "",
    }.get(mode, mode)


def _fmt_pattern_prob(analysis: ReturnAnalysis) -> str:
    v = analysis.prob_next_up_pattern
    if v is None:
        if analysis.pattern_sample_count:
            return f"- (n={analysis.pattern_sample_count})"
        return "-"
    extra = f" (n={analysis.pattern_sample_count})" if analysis.pattern_sample_count else ""
    mode = _pattern_mode_label(analysis.pattern_match_mode)
    plen = analysis.pattern_effective_len or len(analysis.pattern_signature)
    if mode:
        return f"{v:.1f}%{extra} [{mode}/{plen}日]"
    return f"{v:.1f}%{extra}"


def _fmt_vol_prob(v: float | None, n: int, *, blended: bool = False) -> str:
    if v is None:
        return f"- (n={n})" if n else "-"
    tag = "≈" if blended else ""
    return f"{tag}{v:.1f}% (n={n})"


def _print_stock(
    analysis: ReturnAnalysis,
    name_map: dict[str, str],
    *,
    show_detail: bool,
) -> None:
    sym = label_stock(analysis.stock_code, name_map)
    print(f"\n### {sym}")
    if analysis.error:
        print(f"  错误: {analysis.error}")
        return

    print(f"  最新收盘: {analysis.last_close:.2f}  （K 线 {len(analysis.bars)} 根）")

    cum_headers = ["周期"] + [f"{n}日" for n in DEFAULT_CUM_PERIODS]
    cum_vals = ["累计涨幅"] + [
        _fmt_pct(analysis.cumulative_pct.get(n)) for n in DEFAULT_CUM_PERIODS
    ]
    print_table(cum_headers, [cum_vals], aligns=["left"] + ["right"] * len(DEFAULT_CUM_PERIODS))

    print("  【涨跌概率】（统计描述，非投资建议）")
    sig = analysis.pattern_signature or "-"
    plen = analysis.pattern_effective_len or len(sig)
    vp = analysis.volume_prob
    prob_rows = [
        ["近10日收涨占比", _fmt_prob(analysis.prob_recent_10_up), "最近 10 个交易日收涨天数占比"],
        ["历史收涨基准", _fmt_prob(analysis.prob_baseline_up), "样本内收涨比例（不含最新一日）"],
        [
            "形态条件概率",
            _fmt_pattern_prob(analysis),
            f"形态 [{sig}]（有效{plen}日）；不足时缩短/放宽/收缩估计",
        ],
        [
            "量价状态概率",
            _fmt_vol_prob(vp.prob_up_volume_state, vp.sample_volume_state),
            f"近3日量价 [{vp.volume_state_signature or '-'}] 后下一日收涨比例",
        ],
        [
            "收涨放量→次日",
            _fmt_vol_prob(vp.prob_up_after_up_high_vol, vp.sample_up_high_vol),
            "历史「收涨且量比≥1.15」后，下一交易日收涨比例",
        ],
        [
            "连增3日量→次日",
            _fmt_vol_prob(vp.prob_up_after_vol_rising_3d, vp.sample_vol_rising_3d),
            "连续 3 日成交量递增后，下一交易日收涨比例",
        ],
        [
            "近10收涨放量占比",
            _fmt_prob(vp.up_days_volume_confirmed_pct),
            "近10日中，收涨日里成交量高于5日均量的天数占比",
        ],
    ]
    print_table(
        ["指标", "数值", "说明"],
        prob_rows,
        aligns=["left", "right", "left"],
    )

    if show_detail and analysis.recent_10:
        print("  【近 10 个交易日】")
        rows = []
        for r in analysis.recent_10:
            vol_s = "-"
            if r.get("volume") is not None:
                vol_s = str(r["volume"])
            if r.get("vol_ratio") is not None:
                vol_s += f" ({r.get('vol_tag', '')}×{r['vol_ratio']:.2f})"
            rows.append([
                r["date"],
                f"{r['close']:.2f}",
                f"{r['return_pct']:+.2f}%",
                r["direction"],
                vol_s,
            ])
        print_table(
            ["日期", "收盘", "涨跌幅", "方向", "成交量"],
            rows,
            aligns=["left", "right", "right", "center", "right"],
        )


def main() -> int:
    load_env_files()
    parser = argparse.ArgumentParser(
        description="多周期累计涨幅与涨跌概率分析（只读）"
    )
    add_client_args(parser)
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument(
        "--codes",
        default="",
        help="股票代码，逗号分隔",
    )
    src.add_argument(
        "--holdings",
        action="store_true",
        help="从当前账户持仓读取标的（需 API Key）",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=_DEFAULT_COUNT,
        help=f"拉取日 K 根数（默认 {_DEFAULT_COUNT}）",
    )
    parser.add_argument(
        "--dividend-type",
        default="front",
        choices=("none", "front", "back", "front_ratio", "back_ratio"),
        help="复权类型（默认 front）",
    )
    parser.add_argument(
        "--pattern-len",
        type=int,
        default=9,
        help="形态匹配交易日数（默认 9）",
    )
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument("--no-detail", action="store_true", help="不展示近10日明细")
    parser.add_argument(
        "--download-start",
        default=_DEFAULT_DOWNLOAD_START,
        help=f"自动补 K 线时的起始日期 YYYYMMDD（默认 {_DEFAULT_DOWNLOAD_START}）",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="日 K 不足时不自动下载",
    )
    args = parser.parse_args()

    client, account_id = make_client(args, require_api_key=args.holdings)
    codes = _resolve_codes(args, client, account_id)
    bar_map = _ensure_daily_bars(
        client,
        codes,
        args.count,
        args.dividend_type,
        download_start=args.download_start,
        skip_download=args.skip_download,
    )

    analyses: list[ReturnAnalysis] = []
    for code in codes:
        records = _records_for_code(bar_map, code)
        if records:
            analyses.append(
                analyze_stock(code, records, prob_pattern_len=args.pattern_len)
            )
        else:
            analyses.append(ReturnAnalysis(stock_code=code, error="无 K 线数据"))

    name_map = fetch_stock_names(client, codes)

    if args.json:
        print(
            json.dumps(
                {
                    "date": date.today().isoformat(),
                    "source": "holdings" if args.holdings else "codes",
                    "codes": codes,
                    "cum_periods": list(DEFAULT_CUM_PERIODS),
                    "stock_names": name_map,
                    "symbols": [
                        {
                            "stock_code": a.stock_code,
                            "stock_name": name_map.get(a.stock_code, ""),
                            "error": a.error,
                            "last_close": a.last_close,
                            "cumulative_pct": a.cumulative_pct,
                            "prob_recent_10_up": a.prob_recent_10_up,
                            "prob_baseline_up": a.prob_baseline_up,
                            "prob_next_up_pattern": a.prob_next_up_pattern,
                            "pattern_sample_count": a.pattern_sample_count,
                            "pattern_signature": a.pattern_signature,
                            "pattern_effective_len": a.pattern_effective_len,
                            "pattern_match_mode": a.pattern_match_mode,
                            "volume_probability": {
                                "prob_up_volume_state": a.volume_prob.prob_up_volume_state,
                                "volume_state_signature": a.volume_prob.volume_state_signature,
                                "sample_volume_state": a.volume_prob.sample_volume_state,
                                "prob_up_after_up_high_vol": a.volume_prob.prob_up_after_up_high_vol,
                                "sample_up_high_vol": a.volume_prob.sample_up_high_vol,
                                "prob_up_after_vol_rising_3d": a.volume_prob.prob_up_after_vol_rising_3d,
                                "sample_vol_rising_3d": a.volume_prob.sample_vol_rising_3d,
                                "up_days_volume_confirmed_pct": a.volume_prob.up_days_volume_confirmed_pct,
                            },
                            "recent_10": a.recent_10,
                            "bar_count": len(a.bars),
                        }
                        for a in analyses
                    ],
                },
                ensure_ascii=False,
                default=str,
            )
        )
        return 0

    print("=== QMT Bridge 累计涨幅与涨跌概率 ===")
    print(f"日期: {date.today().isoformat()}")
    src_label = "持仓" if args.holdings else "指定标的"
    print(
        f"来源 {src_label} | 标的 {len(codes)} 只 | K线 {args.count} 根 | "
        f"复权 {args.dividend_type} | 形态 {args.pattern_len} 日"
    )

    summary_rows: list[list[str]] = []
    for a in analyses:
        sym = label_stock(a.stock_code, name_map)
        if a.error:
            summary_rows.append([sym, "ERR", "-", "-", "-", "-"])
            continue
        summary_rows.append([
            sym,
            _fmt_pct(a.cumulative_pct.get(1)),
            _fmt_pct(a.cumulative_pct.get(5)),
            _fmt_pct(a.cumulative_pct.get(10)),
            _fmt_pct(a.cumulative_pct.get(30)),
            _fmt_pattern_prob(a) if not a.error else "-",
        ])

    print("\n【汇总】")
    print_table(
        ["标的", "1日", "5日", "10日", "30日", "形态下一日收涨概率"],
        summary_rows,
        aligns=["left", "right", "right", "right", "right", "right"],
    )

    for a in analyses:
        _print_stock(a, name_map, show_detail=not args.no_detail)

    return 0


if __name__ == "__main__":
    sys.exit(main())
