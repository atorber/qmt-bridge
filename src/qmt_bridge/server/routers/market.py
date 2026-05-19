"""行情数据路由模块 /api/market/*。

提供股票/指数的实时快照、K线历史行情、除权因子、逐笔委托簿等端点。
底层调用 xtquant.xtdata 的行情数据接口，包括：
- xtdata.get_full_tick()          — 获取全推行情快照
- xtdata.get_market_data_ex()     — 获取扩展行情数据（返回 DataFrame 字典）
- xtdata.get_local_data()         — 获取本地缓存行情数据
- xtdata.get_divid_factors()      — 获取除权因子
- xtdata.get_market_data()        — 获取行情数据（原始 API）
- xtdata.get_market_data3()       — 获取行情数据 v3
- xtdata.get_full_kline()         — 获取完整 K 线
- xtdata.get_fullspeed_orderbook()— 获取极速委托簿
- xtdata.get_transactioncount()   — 获取逐笔成交计数
"""

import logging
import multiprocessing as mp
import queue
import time

from fastapi import APIRouter, Depends, HTTPException, Query, status
from xtquant import xtdata

from ..config import Settings, get_settings
from ..helpers import _dataframe_dict_to_records, _numpy_to_python

router = APIRouter(prefix="/api/market", tags=["market"])
logger = logging.getLogger("qmt_bridge")

# 主要指数列表（用于 /indices 端点快速查询大盘行情）
MAJOR_INDICES = [
    "000001.SH",  # 上证指数
    "399001.SZ",  # 深证成指
    "399006.SZ",  # 创业板指
    "000300.SH",  # 沪深300
    "000016.SH",  # 上证50
    "000905.SH",  # 中证500
    "000852.SH",  # 中证1000
]


def _divid_factors_worker(
    stock: str,
    start_time: str,
    end_time: str,
    result_queue: mp.Queue,
):
    """子进程执行 xtdata.get_divid_factors，避免主服务线程长时间卡死。"""
    try:
        raw = xtdata.get_divid_factors(stock, start_time=start_time, end_time=end_time)
        result_queue.put(("ok", raw))
    except Exception as exc:  # pragma: no cover - 依赖外部运行时
        result_queue.put(("err", repr(exc)))


def _market_data_worker(
    field_list: list[str],
    stock_list: list[str],
    period: str,
    start_time: str,
    end_time: str,
    count: int,
    dividend_type: str,
    fill_data: bool,
    result_queue: mp.Queue,
):
    """子进程执行 xtdata.get_market_data，避免主服务线程长时间卡死。"""
    try:
        raw = xtdata.get_market_data(
            field_list=field_list,
            stock_list=stock_list,
            period=period,
            start_time=start_time,
            end_time=end_time,
            count=count,
            dividend_type=dividend_type,
            fill_data=fill_data,
        )
        result_queue.put(("ok", raw))
    except Exception as exc:  # pragma: no cover - 依赖外部运行时
        result_queue.put(("err", repr(exc)))


@router.get("/full_tick")
def get_full_tick(
    stocks: str = Query(..., description="股票/指数代码列表，逗号分隔，如 000001.SH,000001.SZ"),
):
    """获取实时全推行情快照。

    Args:
        stocks: 逗号分隔的股票/指数代码，如 "000001.SH,000001.SZ"。

    Returns:
        各代码对应的全推行情数据字典。

    底层调用: xtdata.get_full_tick(code_list=...)
    """
    # 将逗号分隔的代码字符串拆分为列表
    stock_list = [s.strip() for s in stocks.split(",")]
    raw = xtdata.get_full_tick(code_list=stock_list)
    return {"data": _numpy_to_python(raw)}


@router.get("/indices")
def get_major_indices():
    """获取主要指数的实时行情快照。

    返回预定义的主要指数（上证指数、深证成指、创业板指、沪深300 等）的全推行情。

    Returns:
        indices: 指数代码列表。
        data: 各指数的全推行情数据。

    底层调用: xtdata.get_full_tick(code_list=MAJOR_INDICES)
    """
    raw = xtdata.get_full_tick(code_list=MAJOR_INDICES)
    return {"indices": MAJOR_INDICES, "data": _numpy_to_python(raw)}


@router.get("/market_data_ex")
def get_market_data_ex(
    stocks: str = Query(..., description="股票代码列表，逗号分隔，如 000001.SZ,600519.SH"),
    period: str = Query("1d", description="K线周期: tick/1m/5m/15m/30m/60m/1d"),
    start_time: str = Query("", description="开始时间 YYYYMMDD 或 YYYYMMDDHHmmss"),
    end_time: str = Query("", description="结束时间"),
    count: int = Query(-1, description="返回条数，-1 表示不限"),
    dividend_type: str = Query("none", description="除权类型: none/front/back/front_ratio/back_ratio"),
    fill_data: bool = Query(True, description="是否填充空数据"),
):
    """获取扩展 K 线历史行情数据。

    Args:
        stocks: 逗号分隔的股票代码列表。
        period: K 线周期，支持 tick/1m/5m/15m/30m/60m/1d。
        start_time: 开始时间，格式 YYYYMMDD 或 YYYYMMDDHHmmss。
        end_time: 结束时间。
        count: 返回数据条数，-1 表示全部。
        dividend_type: 除权类型（none/front/back/front_ratio/back_ratio）。
        fill_data: 是否对非交易时段进行数据填充。

    Returns:
        按股票代码分组的 K 线记录列表。

    底层调用: xtdata.get_market_data_ex(field_list=[], stock_list=..., ...)
    """
    stock_list = [s.strip() for s in stocks.split(",")]
    raw = xtdata.get_market_data_ex(
        field_list=[],
        stock_list=stock_list,
        period=period,
        start_time=start_time,
        end_time=end_time,
        count=count,
        dividend_type=dividend_type,
        fill_data=fill_data,
    )
    return {"data": _dataframe_dict_to_records(raw)}


@router.get("/local_data")
def get_local_data(
    stocks: str = Query(..., description="股票代码列表，逗号分隔"),
    period: str = Query("1d", description="K线周期"),
    start_time: str = Query("", description="开始时间"),
    end_time: str = Query("", description="结束时间"),
    count: int = Query(-1, description="返回条数"),
    dividend_type: str = Query("none", description="除权类型"),
    fill_data: bool = Query(True, description="是否填充空数据"),
):
    """获取本地缓存的行情数据（不触发网络请求）。

    与 history_ex 的区别在于只读取已下载到本地的数据，不会向服务器请求缺失数据。

    Args:
        stocks: 逗号分隔的股票代码列表。
        period: K 线周期。
        start_time: 开始时间。
        end_time: 结束时间。
        count: 返回数据条数。
        dividend_type: 除权类型。
        fill_data: 是否填充空数据。

    Returns:
        按股票代码分组的本地 K 线记录列表。

    底层调用: xtdata.get_local_data(field_list=[], stock_list=..., ...)
    """
    stock_list = [s.strip() for s in stocks.split(",")]
    raw = xtdata.get_local_data(
        field_list=[],
        stock_list=stock_list,
        period=period,
        start_time=start_time,
        end_time=end_time,
        count=count,
        dividend_type=dividend_type,
        fill_data=fill_data,
    )
    return {"data": _dataframe_dict_to_records(raw)}


@router.get("/divid_factors")
def get_divid_factors(
    stock: str = Query(..., description="股票代码，如 000001.SZ"),
    start_time: str = Query("", description="开始时间"),
    end_time: str = Query("", description="结束时间"),
    timeout_sec: float | None = Query(
        None,
        ge=0.5,
        le=120,
        description="本次调用超时（秒），为空则使用服务端默认配置",
    ),
    settings: Settings = Depends(get_settings),
):
    """获取指定股票的除权因子数据。

    除权因子用于将历史价格进行前/后复权计算。

    Args:
        stock: 单个股票代码。
        start_time: 开始时间。
        end_time: 结束时间。

    Returns:
        该股票在指定时间范围内的除权因子数据。

    底层调用: xtdata.get_divid_factors(stock, start_time=..., end_time=...)
    """
    effective_timeout = timeout_sec or settings.divid_factors_timeout_sec
    start = time.perf_counter()
    ctx = mp.get_context("spawn")
    result_queue: mp.Queue = ctx.Queue(maxsize=1)
    proc = ctx.Process(
        target=_divid_factors_worker,
        args=(stock, start_time, end_time, result_queue),
        daemon=True,
    )
    proc.start()
    proc.join(timeout=effective_timeout)
    elapsed = time.perf_counter() - start

    if proc.is_alive():
        proc.terminate()
        proc.join(timeout=1.0)
        logger.error(
            "market.divid_factors timeout: stock=%s start=%s end=%s elapsed=%.3fs timeout=%.2fs",
            stock,
            start_time,
            end_time,
            elapsed,
            effective_timeout,
        )
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=(
                "xtdata.get_divid_factors timeout, "
                f"exceeded {effective_timeout:.2f}s"
            ),
        )

    if elapsed >= settings.divid_factors_slow_log_sec:
        logger.warning(
            "market.divid_factors slow call: stock=%s start=%s end=%s elapsed=%.3fs",
            stock,
            start_time,
            end_time,
            elapsed,
        )
    else:
        logger.debug(
            "market.divid_factors call: stock=%s start=%s end=%s elapsed=%.3fs",
            stock,
            start_time,
            end_time,
            elapsed,
        )

    try:
        result_status, payload = result_queue.get_nowait()
    except queue.Empty as exc:
        logger.error(
            "market.divid_factors empty result: stock=%s start=%s end=%s elapsed=%.3fs",
            stock,
            start_time,
            end_time,
            elapsed,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="xtdata.get_divid_factors returned no data",
        ) from exc

    if result_status == "err":
        logger.error(
            "market.divid_factors failed: stock=%s start=%s end=%s error=%s",
            stock,
            start_time,
            end_time,
            payload,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"xtdata.get_divid_factors failed: {payload}",
        )

    return {"stock": stock, "data": _numpy_to_python(payload)}


# ---------------------------------------------------------------------------
# 以下为扩展行情端点
# ---------------------------------------------------------------------------


@router.get("/market_data")
def get_market_data(
    stocks: str = Query(..., description="股票代码列表，逗号分隔"),
    fields: str = Query("open,high,low,close,volume", description="字段列表，逗号分隔"),
    period: str = Query("1d", description="K线周期"),
    start_time: str = Query("", description="开始时间"),
    end_time: str = Query("", description="结束时间"),
    count: int = Query(-1, description="返回条数"),
    dividend_type: str = Query("none", description="除权类型"),
    fill_data: bool = Query(True, description="是否填充空数据"),
    timeout_sec: float | None = Query(
        None,
        ge=0.5,
        le=180,
        description="本次调用超时（秒），为空则使用服务端默认配置",
    ),
    settings: Settings = Depends(get_settings),
):
    """通过原始 get_market_data 接口获取行情数据。

    返回格式为 {字段: {股票: numpy 数组}} 的嵌套结构，
    经转换后以记录列表的形式返回。

    Args:
        stocks: 逗号分隔的股票代码列表。
        fields: 逗号分隔的字段列表（如 open,high,low,close,volume）。
        period: K 线周期。
        start_time: 开始时间。
        end_time: 结束时间。
        count: 返回条数。
        dividend_type: 除权类型。
        fill_data: 是否填充空数据。

    Returns:
        按股票代码分组的行情记录列表。

    底层调用: xtdata.get_market_data(field_list=..., stock_list=..., ...)
    """
    from ..helpers import _market_data_to_records

    stock_list = [s.strip() for s in stocks.split(",")]
    field_list = [f.strip() for f in fields.split(",")]
    effective_timeout = timeout_sec or settings.market_data_timeout_sec
    start = time.perf_counter()
    ctx = mp.get_context("spawn")
    result_queue: mp.Queue = ctx.Queue(maxsize=1)
    proc = ctx.Process(
        target=_market_data_worker,
        args=(
            field_list,
            stock_list,
            period,
            start_time,
            end_time,
            count,
            dividend_type,
            fill_data,
            result_queue,
        ),
        daemon=True,
    )
    proc.start()
    proc.join(timeout=effective_timeout)
    elapsed = time.perf_counter() - start

    if proc.is_alive():
        proc.terminate()
        proc.join(timeout=1.0)
        logger.error(
            "market.market_data timeout: stocks=%s period=%s elapsed=%.3fs timeout=%.2fs",
            ",".join(stock_list),
            period,
            elapsed,
            effective_timeout,
        )
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=(
                "xtdata.get_market_data timeout, "
                f"exceeded {effective_timeout:.2f}s"
            ),
        )

    try:
        result_status, payload = result_queue.get_nowait()
    except queue.Empty as exc:
        logger.error(
            "market.market_data empty result: stocks=%s period=%s elapsed=%.3fs",
            ",".join(stock_list),
            period,
            elapsed,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="xtdata.get_market_data returned no data",
        ) from exc

    if result_status == "err":
        logger.error(
            "market.market_data failed: stocks=%s period=%s error=%s",
            ",".join(stock_list),
            period,
            payload,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"xtdata.get_market_data failed: {payload}",
        )

    raw = payload
    records = _market_data_to_records(raw, stock_list, field_list)
    return {"data": records}


@router.get("/market_data3")
def get_market_data3(
    stocks: str = Query(..., description="股票代码列表，逗号分隔"),
    fields: str = Query("", description="字段列表，逗号分隔，为空取全部"),
    period: str = Query("1d", description="K线周期"),
    start_time: str = Query("", description="开始时间"),
    end_time: str = Query("", description="结束时间"),
    count: int = Query(-1, description="返回条数"),
    dividend_type: str = Query("none", description="除权类型"),
    fill_data: bool = Query(True, description="是否填充空数据"),
):
    """通过 get_market_data3 接口获取行情数据（返回 DataFrame 字典）。

    与 market_data 的区别在于返回格式不同，此版本直接返回
    {股票代码: DataFrame} 字典，更便于处理多只股票的数据。

    Args:
        stocks: 逗号分隔的股票代码列表。
        fields: 逗号分隔的字段列表，为空则获取全部字段。
        period: K 线周期。
        start_time: 开始时间。
        end_time: 结束时间。
        count: 返回条数。
        dividend_type: 除权类型。
        fill_data: 是否填充空数据。

    Returns:
        按股票代码分组的行情记录列表。

    底层调用: xtdata.get_market_data3(field_list=..., stock_list=..., ...)
    """
    stock_list = [s.strip() for s in stocks.split(",")]
    # 字段为空字符串时传入空列表，表示获取全部字段
    field_list = [f.strip() for f in fields.split(",") if f.strip()] if fields else []
    raw = xtdata.get_market_data3(
        field_list=field_list,
        stock_list=stock_list,
        period=period,
        start_time=start_time,
        end_time=end_time,
        count=count,
        dividend_type=dividend_type,
        fill_data=fill_data,
    )
    return {"data": _dataframe_dict_to_records(raw)}


@router.get("/full_kline")
def get_full_kline(
    stock: str = Query(..., description="股票代码"),
    period: str = Query("1d", description="K线周期"),
    start_time: str = Query("", description="开始时间"),
    end_time: str = Query("", description="结束时间"),
):
    """获取单只股票的完整 K 线数据。

    Args:
        stock: 单个股票代码。
        period: K 线周期。
        start_time: 开始时间。
        end_time: 结束时间。

    Returns:
        该股票的完整 K 线数据。

    底层调用: xtdata.get_full_kline(stock, period=..., ...)
    """
    raw = xtdata.get_full_kline(stock, period=period, start_time=start_time, end_time=end_time)
    return {"stock": stock, "data": _numpy_to_python(raw)}


@router.get("/fullspeed_orderbook")
def get_fullspeed_orderbook(
    stock: str = Query(..., description="股票代码"),
    start_time: str = Query("", description="开始时间"),
    end_time: str = Query("", description="结束时间"),
):
    """获取极速委托簿数据。

    提供逐笔级别的委托簿快照数据，适用于高频策略分析。

    Args:
        stock: 单个股票代码。
        start_time: 开始时间。
        end_time: 结束时间。

    Returns:
        该股票的极速委托簿数据。

    底层调用: xtdata.get_fullspeed_orderbook(stock, start_time=..., end_time=...)
    """
    raw = xtdata.get_fullspeed_orderbook(stock, start_time=start_time, end_time=end_time)
    return {"stock": stock, "data": _numpy_to_python(raw)}


@router.get("/transactioncount")
def get_transactioncount(
    stock: str = Query(..., description="股票代码"),
    start_time: str = Query("", description="开始时间"),
    end_time: str = Query("", description="结束时间"),
):
    """获取逐笔成交计数数据。

    Args:
        stock: 单个股票代码。
        start_time: 开始时间。
        end_time: 结束时间。

    Returns:
        该股票的逐笔成交计数数据。

    底层调用: xtdata.get_transactioncount(stock, start_time=..., end_time=...)
    """
    raw = xtdata.get_transactioncount(stock, start_time=start_time, end_time=end_time)
    return {"stock": stock, "data": _numpy_to_python(raw)}
