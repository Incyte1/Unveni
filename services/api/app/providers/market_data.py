from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, time, timedelta, timezone
import logging
import math
from zoneinfo import ZoneInfo

import httpx

from app.models import (
    CandleHistoryResponse,
    CandleInterval,
    CandleRecord,
    MarketClock,
    QuoteSnapshot,
    SymbolSearchResponse,
    SymbolSearchResult
)
from app.sample_data import OPPORTUNITIES, QUOTE_FIXTURES


logger = logging.getLogger(__name__)

US_EASTERN = ZoneInfo("America/New_York")
DEFAULT_ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"
INTRADAY_INTERVALS: tuple[CandleInterval, ...] = ("1min", "5min", "15min")
INTERVAL_MINUTES: dict[CandleInterval, int] = {
    "1min": 1,
    "5min": 5,
    "15min": 15,
    "1day": 24 * 60
}


class MarketDataProviderError(RuntimeError):
    pass


class MarketDataProvider:
    source: str
    quality: str

    def search_symbols(self, query: str, limit: int = 10) -> SymbolSearchResponse:
        raise NotImplementedError

    def get_quote(self, symbol: str) -> QuoteSnapshot:
        raise NotImplementedError

    def get_candles(
        self,
        symbol: str,
        interval: CandleInterval,
        limit: int = 60
    ) -> CandleHistoryResponse:
        raise NotImplementedError

    def get_daily_candles(
        self,
        symbol: str,
        limit: int = 60
    ) -> CandleHistoryResponse:
        return self.get_candles(symbol, "1day", limit)

    def get_intraday_candles(
        self,
        symbol: str,
        interval: CandleInterval,
        limit: int = 60
    ) -> CandleHistoryResponse:
        if interval not in INTRADAY_INTERVALS:
            raise MarketDataProviderError(f"Unsupported intraday interval '{interval}'.")
        return self.get_candles(symbol, interval, limit)

    def get_market_clock(self) -> MarketClock:
        raise NotImplementedError


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _symbol_seed(symbol: str) -> int:
    return sum((index + 1) * ord(char) for index, char in enumerate(symbol.upper().strip()))


def _normalize_symbol(symbol: str) -> str:
    return symbol.upper().strip()


def _combine_market_timestamp(trading_day: date, market_time: time) -> datetime:
    return datetime.combine(trading_day, market_time, tzinfo=US_EASTERN).astimezone(timezone.utc)


def _combine_intraday_timestamp(raw_timestamp: str) -> datetime:
    parsed = datetime.strptime(raw_timestamp, "%Y-%m-%d %H:%M:%S")
    return parsed.replace(tzinfo=US_EASTERN).astimezone(timezone.utc)


def _next_business_day(current_day: date) -> date:
    next_day = current_day + timedelta(days=1)
    while next_day.weekday() >= 5:
        next_day += timedelta(days=1)
    return next_day


def _previous_business_day(current_day: date) -> date:
    previous_day = current_day - timedelta(days=1)
    while previous_day.weekday() >= 5:
        previous_day -= timedelta(days=1)
    return previous_day


def _market_close_limit(current_day: date) -> datetime:
    return datetime.combine(current_day, time(hour=20, minute=0), tzinfo=US_EASTERN)


def _market_phase(
    current_time: datetime,
    open_time_value: time,
    close_time_value: time
) -> tuple[str, str, int | None, int | None]:
    today_open = datetime.combine(current_time.date(), open_time_value, tzinfo=US_EASTERN)
    today_close = datetime.combine(current_time.date(), close_time_value, tzinfo=US_EASTERN)
    after_hours_close = _market_close_limit(current_time.date())

    if current_time.weekday() >= 5:
        return ("closed", "closed", None, None)
    if current_time < today_open:
        return ("pre", "premarket", None, int((today_close - current_time).total_seconds() // 60))
    if today_open <= current_time <= today_close:
        minutes_since_open = int((current_time - today_open).total_seconds() // 60)
        minutes_to_close = max(0, int((today_close - current_time).total_seconds() // 60))
        if minutes_since_open < 45:
            phase = "opening_range"
        elif minutes_to_close <= 30:
            phase = "near_close"
        elif minutes_to_close <= 90:
            phase = "power_hour"
        else:
            phase = "midday"
        return ("regular", phase, minutes_since_open, minutes_to_close)
    if current_time <= after_hours_close:
        return ("post", "after_hours", None, None)
    return ("closed", "closed", None, None)


def build_us_market_clock(
    *,
    is_open: bool,
    source: str,
    quality: str,
    fetched_at: datetime | None = None,
    open_time_value: time = time(hour=9, minute=30),
    close_time_value: time = time(hour=16, minute=0)
) -> MarketClock:
    now = (fetched_at or _utc_now()).astimezone(US_EASTERN)
    session, phase, minutes_since_open, minutes_to_close = _market_phase(
        now,
        open_time_value,
        close_time_value
    )

    today_open = datetime.combine(now.date(), open_time_value, tzinfo=US_EASTERN)
    today_close = datetime.combine(now.date(), close_time_value, tzinfo=US_EASTERN)
    if session == "regular":
        next_open_dt = datetime.combine(
            _next_business_day(now.date()),
            open_time_value,
            tzinfo=US_EASTERN
        )
        next_close_dt = today_close
    elif session == "pre":
        next_open_dt = today_open
        next_close_dt = today_close
    else:
        next_open_dt = datetime.combine(
            _next_business_day(now.date()),
            open_time_value,
            tzinfo=US_EASTERN
        )
        next_close_dt = datetime.combine(
            _next_business_day(now.date()),
            close_time_value,
            tzinfo=US_EASTERN
        )

    return MarketClock(
        is_open=is_open and session == "regular",
        session=session,  # type: ignore[arg-type]
        phase=phase,  # type: ignore[arg-type]
        as_of=(fetched_at or _utc_now()),
        next_open=next_open_dt.strftime("%Y-%m-%d %H:%M ET"),
        next_close=next_close_dt.strftime("%Y-%m-%d %H:%M ET"),
        minutes_since_open=minutes_since_open,
        minutes_to_close=minutes_to_close,
        source=source,
        quality=quality  # type: ignore[arg-type]
    )


class FallbackMarketDataProvider(MarketDataProvider):
    source = "fallback-market-data"
    quality = "fallback"

    def search_symbols(self, query: str, limit: int = 10) -> SymbolSearchResponse:
        normalized_query = query.strip().lower()
        known_symbols = {
            *QUOTE_FIXTURES.keys(),
            *(opportunity.symbol for opportunity in OPPORTUNITIES)
        }
        items = []
        for symbol in sorted(known_symbols):
            if not normalized_query or normalized_query in symbol.lower():
                items.append(
                    SymbolSearchResult(
                        symbol=symbol,
                        name=f"{symbol} fallback listing",
                        exchange="NYSE/NASDAQ",
                        asset_type="Equity",
                        region="United States",
                        currency="USD",
                        match_score=1.0 if symbol.lower().startswith(normalized_query) else 0.5,
                        source=self.source,
                        quality="fallback"
                    )
                )
            if len(items) >= limit:
                break

        return SymbolSearchResponse(
            as_of=_utc_now(),
            query=query,
            source=self.source,
            quality="fallback",
            items=items
        )

    def get_quote(self, symbol: str) -> QuoteSnapshot:
        normalized = _normalize_symbol(symbol)
        quote = QUOTE_FIXTURES.get(normalized)
        as_of = _utc_now()

        if quote is None:
            seed = _symbol_seed(normalized)
            last = round(40 + (seed % 900) + ((seed % 100) / 100), 2)
            change_percent = round(((seed % 240) - 120) / 100, 2)
            change = round(last * (change_percent / 100), 2)
            previous_close = round(last - change, 2)
            source = "deterministic-fallback"
        else:
            last = float(quote["last"])
            change = float(quote["change"])
            previous_close = round(last - change, 2)
            change_percent = round((change / previous_close) * 100, 2) if previous_close else 0.0
            source = "fixture-quote"

        return QuoteSnapshot(
            symbol=normalized,
            last=last,
            change=change,
            change_percent=change_percent,
            previous_close=previous_close if previous_close > 0 else None,
            as_of=as_of,
            source=source,
            quality="fallback"
        )

    def get_candles(
        self,
        symbol: str,
        interval: CandleInterval,
        limit: int = 60
    ) -> CandleHistoryResponse:
        if interval == "1day":
            return self._build_daily_candles(symbol, limit)
        return self._build_intraday_candles(symbol, interval, limit)

    def _build_daily_candles(
        self,
        symbol: str,
        limit: int
    ) -> CandleHistoryResponse:
        normalized = _normalize_symbol(symbol)
        quote = self.get_quote(normalized)
        seed = _symbol_seed(normalized)

        closes: list[float] = [quote.previous_close or round(quote.last - quote.change, 2)]
        for index in range(max(limit - 2, 0)):
            cycle = math.sin((seed + index) / 4.0) * 0.012
            bias = (((seed % 11) - 5) / 1000)
            daily_return = cycle + bias
            previous_close = max(5.0, closes[-1] / (1 + daily_return))
            closes.append(round(previous_close, 2))

        closes = list(reversed(closes)) + [quote.last]

        current_day = _utc_now().astimezone(US_EASTERN).date()
        while current_day.weekday() >= 5:
            current_day = _previous_business_day(current_day)
        trading_days: list[date] = [current_day]
        for _ in range(len(closes) - 1):
            trading_days.append(_previous_business_day(trading_days[-1]))
        trading_days.reverse()

        items: list[CandleRecord] = []
        previous_close = closes[0]
        for index, close in enumerate(closes):
            noise = abs(math.sin((seed + index) / 3.0)) * 0.008
            open_price = previous_close if index > 0 else close * (1 - noise / 2)
            high = max(open_price, close) * (1 + noise)
            low = min(open_price, close) * (1 - noise)
            volume = int(1_000_000 + ((_symbol_seed(normalized) * (index + 3)) % 4_000_000))
            items.append(
                CandleRecord(
                    symbol=normalized,
                    interval="1day",
                    timestamp=_combine_market_timestamp(trading_days[index], time(hour=16)),
                    open=round(open_price, 2),
                    high=round(high, 2),
                    low=round(low, 2),
                    close=round(close, 2),
                    volume=volume,
                    source="deterministic-candles",
                    quality="fallback"
                )
            )
            previous_close = close

        return CandleHistoryResponse(
            as_of=_utc_now(),
            symbol=normalized,
            interval="1day",
            source="deterministic-candles",
            quality="fallback",
            items=items[-limit:]
        )

    def _build_intraday_candles(
        self,
        symbol: str,
        interval: CandleInterval,
        limit: int
    ) -> CandleHistoryResponse:
        normalized = _normalize_symbol(symbol)
        quote = self.get_quote(normalized)
        seed = _symbol_seed(normalized)
        step_minutes = INTERVAL_MINUTES[interval]
        now_et = _utc_now().astimezone(US_EASTERN)
        trading_day = now_et.date()
        while trading_day.weekday() >= 5:
            trading_day = _previous_business_day(trading_day)

        if now_et.weekday() >= 5:
            end_dt = _market_close_limit(trading_day)
        else:
            end_dt = min(now_et, _market_close_limit(trading_day))

        start_dt = datetime.combine(trading_day, time(hour=4, minute=0), tzinfo=US_EASTERN)
        cursor = start_dt + timedelta(minutes=step_minutes)
        timestamps: list[datetime] = []
        while cursor <= end_dt:
            timestamps.append(cursor)
            cursor += timedelta(minutes=step_minutes)

        if not timestamps:
            timestamps = [start_dt + timedelta(minutes=step_minutes)]

        items: list[CandleRecord] = []
        previous_close = quote.previous_close or max(5.0, round(quote.last - quote.change, 2))
        session_length = max(1, len(timestamps) - 1)
        previous_bar_close = previous_close

        for index, timestamp in enumerate(timestamps):
            progress = index / session_length
            intraday_wave = math.sin((seed + index) / 3.2) * 0.0028
            bias = (((seed % 9) - 4) / 10000)
            base_price = previous_close + ((quote.last - previous_close) * progress)
            close = max(5.0, base_price * (1 + intraday_wave + bias))
            if index == len(timestamps) - 1:
                close = quote.last

            open_price = previous_bar_close
            noise = abs(math.sin((seed + index) / 2.7)) * 0.0035
            high = max(open_price, close) * (1 + noise)
            low = min(open_price, close) * (1 - noise)
            is_regular = time(hour=9, minute=30) <= timestamp.time() <= time(hour=16, minute=0)
            base_volume = 80_000 if interval == "1min" else 220_000 if interval == "5min" else 500_000
            volume_multiplier = 2.1 if is_regular and timestamp.hour < 11 else 0.8 if not is_regular else 1.0
            volume = int(base_volume * volume_multiplier + ((seed + index * 37) % base_volume))
            items.append(
                CandleRecord(
                    symbol=normalized,
                    interval=interval,
                    timestamp=timestamp.astimezone(timezone.utc),
                    open=round(open_price, 2),
                    high=round(high, 2),
                    low=round(low, 2),
                    close=round(close, 2),
                    volume=volume,
                    source=f"deterministic-{interval}-candles",
                    quality="fallback"
                )
            )
            previous_bar_close = close

        return CandleHistoryResponse(
            as_of=_utc_now(),
            symbol=normalized,
            interval=interval,
            source=f"deterministic-{interval}-candles",
            quality="fallback",
            items=items[-limit:]
        )

    def get_market_clock(self) -> MarketClock:
        now = _utc_now().astimezone(US_EASTERN)
        is_open = now.weekday() < 5 and time(hour=9, minute=30) <= now.time() <= time(hour=16)
        return build_us_market_clock(
            is_open=is_open,
            source="fallback-clock",
            quality="fallback"
        )


ProviderFetchJson = Callable[[dict[str, str]], dict[str, object]]


class AlphaVantageMarketDataProvider(MarketDataProvider):
    source = "alpha-vantage"
    quality = "provider"

    def __init__(
        self,
        *,
        api_key: str,
        timeout_seconds: float,
        intraday_entitlement: str | None = None,
        base_url: str = DEFAULT_ALPHA_VANTAGE_BASE_URL,
        fetch_json: ProviderFetchJson | None = None
    ) -> None:
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.intraday_entitlement = intraday_entitlement
        self.base_url = base_url
        self._fetch_json = fetch_json or self._default_fetch_json

    def _default_fetch_json(self, params: dict[str, str]) -> dict[str, object]:
        response = httpx.get(
            self.base_url,
            params=params,
            timeout=self.timeout_seconds
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise MarketDataProviderError("Market data provider returned an unexpected payload.")
        return payload

    def _request(self, **params: str) -> dict[str, object]:
        try:
            payload = self._fetch_json({
                **params,
                "apikey": self.api_key
            })
        except httpx.TimeoutException as exc:
            raise MarketDataProviderError("Market data request timed out.") from exc
        except httpx.HTTPError as exc:
            raise MarketDataProviderError("Market data request failed.") from exc

        info = payload.get("Information")
        note = payload.get("Note")
        error_message = payload.get("Error Message")
        if isinstance(info, str):
            raise MarketDataProviderError(info)
        if isinstance(note, str):
            raise MarketDataProviderError(note)
        if isinstance(error_message, str):
            raise MarketDataProviderError(error_message)

        return payload

    def search_symbols(self, query: str, limit: int = 10) -> SymbolSearchResponse:
        payload = self._request(function="SYMBOL_SEARCH", keywords=query)
        matches = payload.get("bestMatches")
        if not isinstance(matches, list):
            raise MarketDataProviderError("Symbol search response was missing results.")

        items: list[SymbolSearchResult] = []
        for match in matches:
            if not isinstance(match, dict):
                continue
            region = str(match.get("4. region", ""))
            asset_type = str(match.get("3. type", ""))
            if region != "United States":
                continue
            if asset_type not in {"Equity", "ETF"}:
                continue
            items.append(
                SymbolSearchResult(
                    symbol=str(match.get("1. symbol", "")).upper(),
                    name=str(match.get("2. name", "")).strip(),
                    exchange=str(match.get("4. region", "")).strip(),
                    asset_type=asset_type,
                    region=region,
                    currency=str(match.get("8. currency", "USD")).strip() or "USD",
                    match_score=float(match.get("9. matchScore", 0)) if match.get("9. matchScore") else None,
                    source=self.source,
                    quality="provider"
                )
            )
            if len(items) >= limit:
                break

        return SymbolSearchResponse(
            as_of=_utc_now(),
            query=query,
            source=self.source,
            quality="provider",
            items=items
        )

    def get_quote(self, symbol: str) -> QuoteSnapshot:
        payload = self._request(function="GLOBAL_QUOTE", symbol=_normalize_symbol(symbol))
        raw_quote = payload.get("Global Quote")
        if not isinstance(raw_quote, dict) or not raw_quote:
            raise MarketDataProviderError("Quote response was empty.")

        normalized_symbol = str(raw_quote.get("01. symbol", _normalize_symbol(symbol))).upper()
        price = float(raw_quote["05. price"])
        previous_close = float(raw_quote["08. previous close"])
        change = float(raw_quote.get("09. change", price - previous_close))
        change_percent = float(str(raw_quote.get("10. change percent", "0")).replace("%", ""))
        latest_trading_day = str(raw_quote.get("07. latest trading day", "")).strip()
        trading_day = datetime.strptime(latest_trading_day, "%Y-%m-%d").date() if latest_trading_day else _utc_now().date()

        return QuoteSnapshot(
            symbol=normalized_symbol,
            last=round(price, 4),
            change=round(change, 4),
            change_percent=round(change_percent, 4),
            previous_close=round(previous_close, 4),
            as_of=_combine_market_timestamp(trading_day, time(hour=16)),
            source=self.source,
            quality="provider"
        )

    def get_candles(
        self,
        symbol: str,
        interval: CandleInterval,
        limit: int = 60
    ) -> CandleHistoryResponse:
        normalized_symbol = _normalize_symbol(symbol)
        if interval == "1day":
            return self._get_daily_candles(normalized_symbol, limit)
        return self._get_intraday_candles(normalized_symbol, interval, limit)

    def _get_daily_candles(
        self,
        normalized_symbol: str,
        limit: int
    ) -> CandleHistoryResponse:
        payload = self._request(
            function="TIME_SERIES_DAILY",
            symbol=normalized_symbol,
            outputsize="compact"
        )
        series = payload.get("Time Series (Daily)")
        if not isinstance(series, dict) or not series:
            raise MarketDataProviderError("Candle history response was empty.")

        items: list[CandleRecord] = []
        for timestamp, values in sorted(series.items()):
            if not isinstance(values, dict):
                continue
            trading_day = datetime.strptime(str(timestamp), "%Y-%m-%d").date()
            items.append(
                CandleRecord(
                    symbol=normalized_symbol,
                    interval="1day",
                    timestamp=_combine_market_timestamp(trading_day, time(hour=16)),
                    open=float(values["1. open"]),
                    high=float(values["2. high"]),
                    low=float(values["3. low"]),
                    close=float(values["4. close"]),
                    volume=int(float(values["5. volume"])),
                    source=self.source,
                    quality="provider"
                )
            )

        trimmed = items[-limit:]
        if not trimmed:
            raise MarketDataProviderError("No candle history was returned for the symbol.")

        return CandleHistoryResponse(
            as_of=_utc_now(),
            symbol=normalized_symbol,
            interval="1day",
            source=self.source,
            quality="provider",
            items=trimmed
        )

    def _get_intraday_candles(
        self,
        normalized_symbol: str,
        interval: CandleInterval,
        limit: int
    ) -> CandleHistoryResponse:
        params = {
            "function": "TIME_SERIES_INTRADAY",
            "symbol": normalized_symbol,
            "interval": interval,
            "adjusted": "false",
            "extended_hours": "true",
            "outputsize": "full" if limit > 100 else "compact"
        }
        if self.intraday_entitlement:
            params["entitlement"] = self.intraday_entitlement

        payload = self._request(**params)
        series_key = f"Time Series ({interval})"
        series = payload.get(series_key)
        if not isinstance(series, dict) or not series:
            raise MarketDataProviderError("Intraday candle history response was empty.")

        items: list[CandleRecord] = []
        for timestamp, values in sorted(series.items()):
            if not isinstance(values, dict):
                continue
            items.append(
                CandleRecord(
                    symbol=normalized_symbol,
                    interval=interval,
                    timestamp=_combine_intraday_timestamp(str(timestamp)),
                    open=float(values["1. open"]),
                    high=float(values["2. high"]),
                    low=float(values["3. low"]),
                    close=float(values["4. close"]),
                    volume=int(float(values["5. volume"])),
                    source=self.source,
                    quality="provider"
                )
            )

        trimmed = items[-limit:]
        if not trimmed:
            raise MarketDataProviderError("No intraday candle history was returned for the symbol.")

        return CandleHistoryResponse(
            as_of=_utc_now(),
            symbol=normalized_symbol,
            interval=interval,
            source=self.source,
            quality="provider",
            items=trimmed
        )

    def get_market_clock(self) -> MarketClock:
        payload = self._request(function="MARKET_STATUS")
        markets = payload.get("markets")
        if not isinstance(markets, list):
            raise MarketDataProviderError("Market clock response was missing markets.")

        us_equity_market = next(
            (
                market
                for market in markets
                if isinstance(market, dict)
                and market.get("market_type") == "Equity"
                and market.get("region") == "United States"
            ),
            None
        )
        if not isinstance(us_equity_market, dict):
            raise MarketDataProviderError("United States equity market status was missing.")

        status = str(us_equity_market.get("current_status", "closed")).strip().lower()
        local_open = str(us_equity_market.get("local_open", "09:30"))
        local_close = str(us_equity_market.get("local_close", "16:00"))
        open_hour, open_minute = (int(part) for part in local_open.split(":", maxsplit=1))
        close_hour, close_minute = (int(part) for part in local_close.split(":", maxsplit=1))

        return build_us_market_clock(
            is_open=status == "open",
            source=self.source,
            quality="provider",
            fetched_at=_utc_now(),
            open_time_value=time(hour=open_hour, minute=open_minute),
            close_time_value=time(hour=close_hour, minute=close_minute)
        )
