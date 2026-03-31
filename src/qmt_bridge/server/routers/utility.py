"""工具类路由模块 /api/utility/*。

提供股票名称查询、代码归属市场判断、股票搜索等实用工具端点。
底层调用 xtquant.xtdata 的合约信息接口，包括：
- xtdata.get_instrument_detail()      — 获取单个合约详情（提取中文名称）
- xtdata.get_instrument_type()        — 获取合约类型
- xtdata.get_stock_list_in_sector()   — 获取板块成分股（用于搜索）
"""

import logging
import re

from fastapi import APIRouter, Query
from xtquant import xtdata


logger = logging.getLogger("qmt_bridge")
router = APIRouter(prefix="/api/utility", tags=["utility"])

# 板块 -> {股票代码: 中文名称} 的懒加载缓存，首次搜索中文关键字时构建
_sector_name_cache: dict[str, dict[str, str]] = {}


def _has_chinese(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def _get_name_cache(category: str) -> dict[str, str]:
    """获取或构建板块内 股票代码->中文名称 的映射缓存。"""
    if category not in _sector_name_cache:
        all_stocks = xtdata.get_stock_list_in_sector(category)
        logger.info("正在为板块 '%s' 构建名称缓存 (%d 只股票)…", category, len(all_stocks))
        mapping = {}
        for code in all_stocks:
            detail = xtdata.get_instrument_detail(code)
            name = detail.get("InstrumentName", "") if isinstance(detail, dict) else ""
            mapping[code] = name
        _sector_name_cache[category] = mapping
        logger.info("板块 '%s' 名称缓存构建完成", category)
    return _sector_name_cache[category]


@router.get("/stock_name")
def get_stock_name(
    stock: str = Query(..., description="股票代码"),
):
    """获取股票的中文名称。

    Args:
        stock: 股票代码。

    Returns:
        stock: 股票代码。
        name: 股票中文名称。

    底层调用: xtdata.get_instrument_detail(stock)
    """
    detail = xtdata.get_instrument_detail(stock)
    # 从合约详情中提取 InstrumentName 字段作为中文名称
    name = detail.get("InstrumentName", "") if isinstance(detail, dict) else ""
    return {"stock": stock, "name": name}


@router.get("/batch_stock_name")
def get_batch_stock_name(
    stocks: str = Query(..., description="股票代码列表，逗号分隔"),
):
    """批量获取多只股票的中文名称。

    Args:
        stocks: 逗号分隔的股票代码列表。

    Returns:
        data: {股票代码: 中文名称} 的映射字典。

    底层调用: xtdata.get_instrument_detail(stock)（逐只查询）
    """
    stock_list = [s.strip() for s in stocks.split(",")]
    result = {}
    for code in stock_list:
        detail = xtdata.get_instrument_detail(code)
        result[code] = detail.get("InstrumentName", "") if isinstance(detail, dict) else ""
    return {"data": result}


@router.get("/code_to_market")
def code_to_market(
    stock: str = Query(..., description="股票代码"),
):
    """判断股票代码所属的市场。

    通过代码后缀（如 .SH、.SZ）和合约类型判断市场归属。

    Args:
        stock: 股票代码。

    Returns:
        stock: 股票代码。
        market: 市场代码（如 SH、SZ）。
        type: 合约类型。

    底层调用: xtdata.get_instrument_type(stock)
    """
    instrument_type = xtdata.get_instrument_type(stock)
    # 从代码后缀中提取市场代码
    market = stock.split(".")[-1] if "." in stock else ""
    return {"stock": stock, "market": market, "type": instrument_type}


@router.get("/search")
def search_stocks(
    keyword: str = Query(..., description="搜索关键字（代码或名称）"),
    category: str = Query("沪深A股", description="搜索范围"),
    limit: int = Query(20, description="返回条数上限"),
):
    """按关键字搜索股票代码。

    在指定板块（类别）范围内，按代码前缀或中文名称模糊匹配搜索股票。

    - 中文关键字：同时匹配代码和名称（首次调用会构建名称缓存，耗时数秒）
    - 非中文关键字：仅匹配代码（快速路径）

    Args:
        keyword: 搜索关键字（股票代码前缀或名称片段）。
        category: 搜索范围板块名称，默认 "沪深A股"。
        limit: 最多返回的结果数量。

    Returns:
        keyword: 搜索关键字。
        count: 匹配结果数量（受 limit 限制）。
        stocks: 匹配的股票代码列表。

    底层调用: xtdata.get_stock_list_in_sector(category),
              xtdata.get_instrument_detail(stock)（名称缓存构建时）
    """
    keyword_upper = keyword.upper()

    if _has_chinese(keyword):
        name_cache = _get_name_cache(category)
        matches = [
            code
            for code, name in name_cache.items()
            if keyword in name or keyword_upper in code.upper()
        ]
    else:
        all_stocks = xtdata.get_stock_list_in_sector(category)
        matches = [s for s in all_stocks if keyword_upper in s.upper()]

    return {"keyword": keyword, "count": len(matches[:limit]), "stocks": matches[:limit]}
