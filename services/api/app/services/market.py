from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, time, timezone
from functools import lru_cache
import logging
from threading import Lock
from typing import TypeVar
from zoneinfo import ZoneInfo

from app.config import settings
from app.errors import AppError
from app.models import (
    CandleHistoryResponse,
    CandleInterval,
    MarketBenchmark,
    MarketClock,
    MarketEvent,
    MarketOverviewResponse,
    MarketRegime,
    QuoteSnapshot,
    RiskSnapshot,
    SessionResponse,
    SymbolSearchResponse
)
from app.providers.market_data import (
    AlphaVantageMarketDataProvider,
    FallbackMarketDataProvider,
    INTRADAY_INTERVALS,
    MarketDataProvider,
    MarketDataProviderError
)
from app.sample_data import RISK


logger = logging.getLogger(__name__)

US_EASTERN = ZoneInfo("America/New_York")
T = TypeVar("T")

CACHE_SECONDS = {
    "quote": 20,
    "candles": 120,
    "clock": 30,
    "search": 300
}


class MarketDataGateway:
    def __init__(
        self,
        *,
        primary_provider: MarketDataProvider | None,
        fallback_provider: MarketDataProvider,
        allow_fallback: bool
    ) -> None:
        self.primary_provider = primary_provider
        self.fallback_provider = fallback_provider
        self.allow_fallback = allow_fallback
        self._cache: dict[tuple[str, str], tuple[float, object]] = {}
        self._lock = Lock()

        if self.primary_provider is None and settings.data_provider == "alpha_vantage":
            if self.allow_fallback:
                logger.warning(
                    "ALPHA_VANTAGE_API_KEY is not configured; market data is using explicit development fallback mode."
                )
            else:
                raise AppError(
                    code="market_data_not_configured",
                    message="Market data provider is configured but API credentials are missing.",
                    status_code=503
                )

    def _cache_key(self, namespace: str, key: str) -> tuple[str, str]:
        return (namespace, key)

    def _cached(self, namespace: str, key: str, loader: Callable[[], T]) -> T:
        ttl_seconds = CACHE_SECONDS[namespace]
        now = datetime.now(timezone.utc).timestamp()
        cache_key = self._cache_key(namespace, key)

        with self._lock:
            cached = self._cache.get(cache_key)
            if cached and cached[0] > now:
                return cached[1]  # type: ignore[return-value]

        value = loader()

        with self._lock:
            self._cache[cache_key] = (now + ttl_seconds, value)

        return value

    def _load(
        self,
        *,
        operation: str,
        key: str,
        primary_loader: Callable[[MarketDataProvider], T],
        fallback_loader: Callable[[MarketDataProvider], T]
    ) -> T:
        def loader() -> T:
            if self.primary_provider is None:
                return fallback_loader(self.fallback_provider)

            try:
                return primary_loader(self.primary_provider)
            except MarketDataProviderError as exc:
                if self.allow_fallback:
                    logger.warning(
                        "Market data provider failed during %s for %s; falling back to development data. Error: %s",
                        operation,
                        key,
                        exc
                    )
                    return fallback_loader(self.fallback_provider)
                raise AppError(
                    code="market_data_unavailable",
                    message="The market data provider is unavailable right now.",
                    status_code=503
                ) from exc

        return self._cached(operation, key, loader)

    def search_symbols(self, query: str, limit: int = 10) -> SymbolSearchResponse:
        trimmed = query.strip()
        return self._load(
            operation="search",
            key=f"{trimmed}:{limit}",
            primary_loader=lambda provider: provider.search_symbols(trimmed, limit),
            fallback_loader=lambda provider: provider.search_symbols(trimmed, limit)
        )

    def get_quote(self, symbol: str) -> QuoteSnapshot:
        normalized = symbol.upper().strip()
        return self._load(
            operation="quote",
            key=normalized,
            primary_loader=lambda provider: provider.get_quote(normalized),
            fallback_loader=lambda provider: provider.get_quote(normalized)
        )

    def get_candles(
        self,
        symbol: str,
        interval: CandleInterval,
        limit: int = 60
    ) -> CandleHistoryResponse:
        normalized = symbol.upper().strip()
        return self._load(
            operation="candles",
            key=f"{normalized}:{interval}:{limit}",
            primary_loader=lambda provider: provider.get_candles(normalized, interval, limit),
            fallback_loader=lambda provider: provider.get_candles(normalized, interval, limit)
        )

    def get_market_clock(self) -> MarketClock:
        return self._load(
            operation="clock",
            key="us-equities",
            primary_loader=lambda provider: provider.get_market_clock(),
            fallback_loader=lambda provider: provider.get_market_clock()
        )


@lru_cache
def get_market_data_gateway() -> MarketDataGateway:
    primary_provider: MarketDataProvider | None = None
    if settings.data_provider == "alpha_vantage" and settings.alpha_vantage_api_key:
        primary_provider = AlphaVantageMarketDataProvider(
            api_key=settings.alpha_vantage_api_key,
            timeout_seconds=settings.market_data_timeout_seconds,
            intraday_entitlement=settings.alpha_vantage_intraday_entitlement
        )

    return MarketDataGateway(
        primary_provider=primary_provider,
        fallback_provider=FallbackMarketDataProvider(),
        allow_fallback=settings.allow_market_data_fallback or settings.data_provider == "mock"
    )


def reset_market_data_gateway() -> None:
    get_market_data_gateway.cache_clear()


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _return_pct(current: float, previous: float) -> float:
    if previous == 0:
        return 0.0
    return ((current / previous) - 1) * 100


def _to_eastern(timestamp: datetime) -> datetime:
    return timestamp.astimezone(US_EASTERN)


def _is_regular_session_bar(timestamp: datetime) -> bool:
    local_timestamp = _to_eastern(timestamp)
    return time(hour=9, minute=30) <= local_timestamp.time() <= time(hour=16, minute=0)


def _regular_session_items(candles: CandleHistoryResponse) -> list:
    return [item for item in candles.items if _is_regular_session_bar(item.timestamp)]


def _opening_range(candles: CandleHistoryResponse) -> tuple[float | None, float | None]:
    regular_session = _regular_session_items(candles)
    if len(regular_session) < 3:
        return (None, None)
    opening_bars = regular_session[:3]
    return (
        max(item.high for item in opening_bars),
        min(item.low for item in opening_bars)
    )


def _vwap(candles: CandleHistoryResponse) -> float | None:
    regular_session = _regular_session_items(candles)
    if not regular_session:
        return None

    cumulative_pv = 0.0
    cumulative_volume = 0
    for item in regular_session:
        typical_price = (item.high + item.low + item.close) / 3
        cumulative_pv += typical_price * item.volume
        cumulative_volume += item.volume

    if cumulative_volume == 0:
        return None
    return cumulative_pv / cumulative_volume


def search_symbols(query: str, limit: int = 10) -> SymbolSearchResponse:
    return get_market_data_gateway().search_symbols(query, limit)


def get_candle_history(
    symbol: str,
    interval: CandleInterval,
    limit: int = 60
) -> CandleHistoryResponse:
    return get_market_data_gateway().get_candles(symbol, interval, limit)


def get_daily_candle_history(symbol: str, limit: int = 60) -> CandleHistoryResponse:
    return get_candle_history(symbol, "1day", limit)


def get_intraday_candle_history(
    symbol: str,
    interval: CandleInterval,
    limit: int = 60
) -> CandleHistoryResponse:
    if interval not in INTRADAY_INTERVALS:
        raise AppError(
            code="invalid_interval",
            message="Use an intraday interval of 1min, 5min, or 15min.",
            status_code=400
        )
    return get_candle_history(symbol, interval, limit)


def get_market_clock() -> MarketClock:
    return get_market_data_gateway().get_market_clock()


def get_quote_snapshot(symbol: str) -> QuoteSnapshot:
    intraday = get_intraday_candle_history(symbol, "1min", 2)
    provider_quote = get_market_data_gateway().get_quote(symbol)
    if intraday.items:
        latest = intraday.items[-1]
        previous_close = provider_quote.previous_close
        change = round(latest.close - (previous_close or latest.open), 4)
        change_percent = round(
            _return_pct(latest.close, previous_close or latest.open),
            4
        )
        quality = "provider" if intraday.quality == "provider" and provider_quote.quality == "provider" else intraday.quality
        source = f"{intraday.source}-{intraday.interval}-close"
        return QuoteSnapshot(
            symbol=latest.symbol,
            last=latest.close,
            change=change,
            change_percent=change_percent,
            previous_close=previous_close,
            as_of=latest.timestamp,
            source=source,
            quality=quality  # type: ignore[arg-type]
        )

    return provider_quote


def _benchmark_note(symbol: str, quote: QuoteSnapshot, candles: CandleHistoryResponse) -> str:
    vwap = _vwap(candles)
    opening_range_high, opening_range_low = _opening_range(candles)
    price_location = "above" if vwap is not None and quote.last >= vwap else "below"
    opening_range_note = (
        f" clearing the opening range high at {opening_range_high:.2f}"
        if opening_range_high is not None and quote.last >= opening_range_high
        else (
            f" below the opening range low at {opening_range_low:.2f}"
            if opening_range_low is not None and quote.last <= opening_range_low
            else " still inside the opening range"
        )
    )
    return (
        f"{symbol} is {price_location} intraday VWAP"
        f"{f' near {vwap:.2f}' if vwap is not None else ''} and{opening_range_note}."
    )


def get_market_overview() -> MarketOverviewResponse:
    clock = get_market_clock()
    benchmark_symbols = ("SPY", "QQQ", "IWM")
    benchmark_quotes = [get_quote_snapshot(symbol) for symbol in benchmark_symbols]
    benchmark_candles = {
        symbol: get_intraday_candle_history(symbol, "5min", 96)
        for symbol in benchmark_symbols
    }

    above_vwap_count = 0
    clearing_opening_range_count = 0
    session_moves: list[float] = []
    session_ranges: list[float] = []
    benchmarks: list[MarketBenchmark] = []

    for quote in benchmark_quotes:
        candles = benchmark_candles[quote.symbol]
        regular_session = _regular_session_items(candles)
        vwap = _vwap(candles)
        opening_range_high, opening_range_low = _opening_range(candles)
        session_open = regular_session[0].open if regular_session else (quote.previous_close or quote.last)
        session_moves.append(_return_pct(quote.last, session_open))
        session_high = max((item.high for item in regular_session), default=quote.last)
        session_low = min((item.low for item in regular_session), default=quote.last)
        if session_low:
            session_ranges.append(_return_pct(session_high, session_low))
        if vwap is not None and quote.last >= vwap:
            above_vwap_count += 1
        if opening_range_high is not None and quote.last >= opening_range_high:
            clearing_opening_range_count += 1

        benchmarks.append(
            MarketBenchmark(
                symbol=quote.symbol,
                move_pct=round(session_moves[-1], 2),
                note=_benchmark_note(quote.symbol, quote, candles)
            )
        )

    average_session_move = _mean(session_moves)
    average_session_range = _mean(session_ranges)

    if clock.phase == "premarket":
        headline = "Premarket preparation only"
        summary = "Premarket tape is useful for planning, but fresh day trades should wait for the opening range to form."
    elif clock.phase == "near_close":
        headline = "Near-close tape favors defense"
        summary = "Fresh entries are lower quality late in the session, so risk should shift toward exits and flattening."
    elif above_vwap_count >= 2 and clearing_opening_range_count >= 2 and average_session_move >= 0:
        headline = "Constructive intraday tape with follow-through"
        summary = "Benchmark breadth is holding above VWAP and opening ranges, so long intraday continuation setups have better odds."
    elif above_vwap_count <= 1 and average_session_move < 0:
        headline = "Weak intraday tape with failed bids"
        summary = "Benchmark breadth is not holding intraday support, so bullish setups should stay selective or be avoided."
    else:
        headline = "Mixed intraday tape"
        summary = "The market is trading without broad intraday alignment, so only the cleanest setups should stay in play."

    if average_session_range >= 2.8:
        volatility_regime = f"Wide intraday range at {average_session_range:.2f}% keeps stops tight and entries selective."
    elif average_session_range >= 1.4:
        volatility_regime = f"Normal intraday range at {average_session_range:.2f}% supports standard day-trade sizing."
    else:
        volatility_regime = f"Compressed intraday range at {average_session_range:.2f}% can lead to false breakouts and slower follow-through."

    breadth_regime = (
        f"{above_vwap_count}/3 benchmarks are above intraday VWAP and "
        f"{clearing_opening_range_count}/3 are pressing above the opening range."
    )

    highlights = [
        f"Session phase is {clock.phase.replace('_', ' ')} with {clock.minutes_to_close if clock.minutes_to_close is not None else 'n/a'} minutes to the close.",
        f"Average benchmark move from today's open is {average_session_move:.2f}%.",
        f"Average benchmark session range is {average_session_range:.2f}%."
    ]

    upcoming_events = [
        MarketEvent(
            label="Opening range completes" if clock.phase == "opening_range" else "Market close",
            scheduled_at=clock.next_close if clock.is_open else (clock.next_open or "Unknown"),
            impact="medium" if clock.phase in {"opening_range", "near_close"} else "low"
        )
    ]

    quality = (
        "provider"
        if all(quote.quality == "provider" for quote in benchmark_quotes)
        and all(candles.quality == "provider" for candles in benchmark_candles.values())
        and clock.quality == "provider"
        else "fallback"
    )
    source = "alpha-vantage-intraday-derived" if quality == "provider" else "fallback-intraday-derived"

    return MarketOverviewResponse(
        as_of=datetime.now(timezone.utc),
        source=source,
        quality=quality,  # type: ignore[arg-type]
        clock=clock,
        regime=MarketRegime(
            headline=headline,
            summary=summary,
            volatility_regime=volatility_regime,
            breadth_regime=breadth_regime
        ),
        benchmarks=benchmarks,
        highlights=highlights,
        upcoming_events=upcoming_events
    )


def get_risk_snapshot(session: SessionResponse) -> RiskSnapshot:
    return RISK.model_copy(
        update={
            "execution_mode": session.execution_mode,
            "entitlement": session.entitlement
        }
    )
