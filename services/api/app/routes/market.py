from fastapi import APIRouter, Query

from app.models import CandleHistoryResponse, CandleInterval, MarketClock, MarketOverviewResponse, QuoteSnapshot, SymbolSearchResponse
from app.services.market import (
    get_candle_history,
    get_daily_candle_history,
    get_intraday_candle_history,
    get_market_clock,
    get_market_overview,
    get_quote_snapshot,
    search_symbols
)

router = APIRouter(tags=["market"])


@router.get("/market-overview", response_model=MarketOverviewResponse)
def market_overview() -> MarketOverviewResponse:
    return get_market_overview()


@router.get("/market/clock", response_model=MarketClock)
def market_clock() -> MarketClock:
    return get_market_clock()


@router.get("/market/search", response_model=SymbolSearchResponse)
def market_symbol_search(
    q: str = Query(min_length=1, max_length=32),
    limit: int = Query(default=10, ge=1, le=20)
) -> SymbolSearchResponse:
    return search_symbols(q, limit)


@router.get("/market/quotes/{symbol}", response_model=QuoteSnapshot)
def market_quote(symbol: str) -> QuoteSnapshot:
    return get_quote_snapshot(symbol)


@router.get("/market/candles/{symbol}", response_model=CandleHistoryResponse)
def market_candles(
    symbol: str,
    interval: CandleInterval = Query(default="1day"),
    limit: int = Query(default=60, ge=5, le=120)
) -> CandleHistoryResponse:
    if interval == "1day":
        return get_daily_candle_history(symbol, limit)
    if interval in {"1min", "5min", "15min"}:
        return get_intraday_candle_history(symbol, interval, limit)
    return get_candle_history(symbol, interval, limit)
