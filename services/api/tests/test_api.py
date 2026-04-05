from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.db import Database, database
from app.errors import DatabaseError
from app.main import app
from app.migrations import MigrationManager
from app.models import (
    CandleHistoryResponse,
    CandleInterval,
    CandleRecord,
    ExposureBucket,
    IntradayFeatureSnapshot,
    MarketClock,
    MarketOverviewResponse,
    MarketRegime,
    QuoteSnapshot,
    RiskSnapshot,
    SignalPortfolioState,
    SymbolSearchResponse,
    SymbolSearchResult
)
from app.providers.market_data import AlphaVantageMarketDataProvider, FallbackMarketDataProvider
from app.repositories.watchlist import WatchlistRepository
from app.services.intraday_features import IntradayFeatureBundle
from app.services import market as market_service
from app.services.market import MarketDataGateway
from app.services.signals import RuleBasedIntradaySignalEngine, SignalContext

DATA_TABLES = [
    "audit_events",
    "signal_alerts",
    "signal_snapshots",
    "sessions",
    "users",
    "paper_fills",
    "paper_orders",
    "paper_positions",
    "watchlist_items",
    "watchlists"
]


@pytest.fixture(autouse=True)
def clean_database() -> None:
    market_service.reset_market_data_gateway()
    MigrationManager(database).apply_pending()
    with database.session() as session:
        for table in DATA_TABLES:
            session.execute(f"DELETE FROM {table}")

    yield

    market_service.reset_market_data_gateway()
    with database.session() as session:
        for table in DATA_TABLES:
            session.execute(f"DELETE FROM {table}")


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def start_session(
    client: TestClient,
    handle: str = "operator-1",
    display_name: str = "Operator One",
    access_token: str | None = None
) -> dict[str, object]:
    payload: dict[str, object] = {
        "handle": handle,
        "display_name": display_name
    }
    if access_token is not None:
        payload["access_token"] = access_token

    response = client.post("/session", json=payload)
    assert response.status_code == 201
    return response.json()


def signal_by_symbol(payload: dict[str, object], symbol: str) -> dict[str, object]:
    return next(
        item
        for item in payload["items"]  # type: ignore[index]
        if item["symbol"] == symbol
    )


def build_quote(
    symbol: str,
    *,
    last: float,
    previous_close: float,
    source: str = "alpha-vantage",
    quality: str = "provider"
) -> QuoteSnapshot:
    change = round(last - previous_close, 4)
    change_percent = round((change / previous_close) * 100, 4) if previous_close else 0.0
    return QuoteSnapshot(
        symbol=symbol,
        last=last,
        change=change,
        change_percent=change_percent,
        previous_close=previous_close,
        as_of=datetime.now(timezone.utc),
        source=source,
        quality=quality  # type: ignore[arg-type]
    )


def build_candles(
    symbol: str,
    closes: list[float],
    *,
    interval: CandleInterval = "1day",
    start: datetime | None = None,
    source: str = "alpha-vantage",
    quality: str = "provider",
    volumes: list[int] | None = None
) -> CandleHistoryResponse:
    default_start = (
        datetime(2026, 1, 2, 14, 30, tzinfo=timezone.utc)
        if interval != "1day"
        else datetime(2026, 1, 2, 21, 0, tzinfo=timezone.utc)
    )
    start_time = start or default_start
    step_minutes = {
        "1min": 1,
        "5min": 5,
        "15min": 15,
        "1day": 24 * 60
    }[interval]
    wick_pct = {
        "1min": 0.0015,
        "5min": 0.002,
        "15min": 0.003,
        "1day": 0.01
    }[interval]
    first_open_factor = 0.999 if interval != "1day" else 0.995
    items = []
    previous_close = closes[0]
    for index, close in enumerate(closes):
        open_price = previous_close if index > 0 else close * first_open_factor
        high = max(open_price, close) * (1 + wick_pct)
        low = min(open_price, close) * (1 - wick_pct)
        items.append(
            CandleRecord(
                symbol=symbol,
                interval=interval,
                timestamp=start_time + timedelta(minutes=step_minutes * index),
                open=round(open_price, 2),
                high=round(high, 2),
                low=round(low, 2),
                close=round(close, 2),
                volume=volumes[index] if volumes is not None else 1_000_000 + (index * 1_000),
                source=source,
                quality=quality  # type: ignore[arg-type]
            )
        )
        previous_close = close

    return CandleHistoryResponse(
        as_of=datetime.now(timezone.utc),
        symbol=symbol,
        interval=interval,
        source=source,
        quality=quality,  # type: ignore[arg-type]
        items=items
    )


class FakeMarketDataGateway:
    def __init__(
        self,
        quotes: dict[str, QuoteSnapshot],
        candles: dict[tuple[str, CandleInterval], CandleHistoryResponse],
        *,
        is_open: bool = False,
        phase: str = "midday",
        minutes_to_close: int | None = 180
    ) -> None:
        self.quotes = quotes
        self.candles = candles
        self.clock = MarketClock(
            is_open=is_open,
            session="regular" if is_open else "closed",
            phase=phase,  # type: ignore[arg-type]
            as_of=datetime.now(timezone.utc),
            next_open="2026-04-06 09:30 ET",
            next_close="2026-04-06 16:00 ET",
            minutes_since_open=90 if is_open else None,
            minutes_to_close=minutes_to_close,
            source="alpha-vantage",
            quality="provider"
        )

    def search_symbols(self, query: str, limit: int = 10) -> SymbolSearchResponse:
        query_lower = query.lower()
        items = [
            SymbolSearchResult(
                symbol=symbol,
                name=f"{symbol} Corp",
                exchange="NASDAQ",
                asset_type="Equity",
                region="United States",
                currency="USD",
                match_score=1.0,
                source="alpha-vantage",
                quality="provider"
            )
            for symbol in self.quotes
            if query_lower in symbol.lower()
        ][:limit]
        return SymbolSearchResponse(
            as_of=datetime.now(timezone.utc),
            query=query,
            source="alpha-vantage",
            quality="provider",
            items=items
        )

    def get_quote(self, symbol: str) -> QuoteSnapshot:
        return self.quotes[symbol.upper()]

    def get_candles(self, symbol: str, interval: CandleInterval, limit: int = 60) -> CandleHistoryResponse:
        candles = self.candles[(symbol.upper(), interval)]
        return candles.model_copy(update={"items": candles.items[-limit:]})

    def get_market_clock(self) -> MarketClock:
        return self.clock


def build_signal_gateway(
    *,
    is_open: bool = True,
    phase: str = "midday",
    minutes_to_close: int | None = 180,
    quote_overrides: dict[str, tuple[float, float]] | None = None,
    candle_overrides: dict[tuple[str, CandleInterval], CandleHistoryResponse] | None = None
) -> FakeMarketDataGateway:
    quotes = {
        "NVDA": build_quote("NVDA", last=980.0, previous_close=965.0),
        "AAPL": build_quote("AAPL", last=184.0, previous_close=190.0),
        "SPY": build_quote("SPY", last=530.0, previous_close=525.0),
        "QQQ": build_quote("QQQ", last=460.0, previous_close=455.0),
        "IWM": build_quote("IWM", last=209.0, previous_close=207.5)
    }
    for symbol, values in (quote_overrides or {}).items():
        last, previous_close = values
        quotes[symbol] = build_quote(symbol, last=last, previous_close=previous_close)

    candles: dict[tuple[str, CandleInterval], CandleHistoryResponse] = {
        ("NVDA", "1min"): build_candles("NVDA", [978.8, 979.5, 980.0], interval="1min"),
        ("NVDA", "5min"): build_candles(
            "NVDA",
            [970, 972, 973, 974, 976, 978, 981, 984],
            interval="5min",
            volumes=[120000, 130000, 140000, 150000, 170000, 240000, 260000, 280000]
        ),
        ("NVDA", "15min"): build_candles("NVDA", [965, 968, 971, 975, 979, 983], interval="15min"),
        ("NVDA", "1day"): build_candles("NVDA", [940, 950, 958, 965]),
        ("AAPL", "1min"): build_candles("AAPL", [186.2, 185.1, 184.0], interval="1min"),
        ("AAPL", "5min"): build_candles("AAPL", [191, 190.5, 189.8, 188.9, 187.5, 186.1, 185.0, 184.0], interval="5min"),
        ("AAPL", "15min"): build_candles("AAPL", [194, 192, 190, 188, 186, 184.5], interval="15min"),
        ("AAPL", "1day"): build_candles("AAPL", [198, 195, 192, 190]),
        ("SPY", "1min"): build_candles("SPY", [528.4, 529.2, 530.0], interval="1min"),
        ("SPY", "5min"): build_candles("SPY", [525.2, 525.8, 526.1, 527.0, 528.0, 529.0, 529.5, 530.0], interval="5min"),
        ("SPY", "15min"): build_candles("SPY", [523, 524, 525.2, 526.8, 528.2, 529.4], interval="15min"),
        ("SPY", "1day"): build_candles("SPY", [520, 522, 523, 525]),
        ("QQQ", "1min"): build_candles("QQQ", [458.4, 459.0, 460.0], interval="1min"),
        ("QQQ", "5min"): build_candles("QQQ", [455.2, 456.1, 456.8, 457.5, 458.4, 459.1, 459.4, 460.0], interval="5min"),
        ("QQQ", "15min"): build_candles("QQQ", [452, 453.5, 455.0, 456.8, 458.2, 459.6], interval="15min"),
        ("QQQ", "1day"): build_candles("QQQ", [448, 450, 452, 455]),
        ("IWM", "1min"): build_candles("IWM", [208.2, 208.7, 209.0], interval="1min"),
        ("IWM", "5min"): build_candles("IWM", [206.8, 207.0, 207.2, 207.5, 207.9, 208.3, 208.7, 209.0], interval="5min"),
        ("IWM", "15min"): build_candles("IWM", [205.6, 206.2, 206.9, 207.5, 208.2, 208.9], interval="15min"),
        ("IWM", "1day"): build_candles("IWM", [203, 204, 205, 207.5])
    }
    candles.update(candle_overrides or {})

    return FakeMarketDataGateway(
        quotes=quotes,
        candles=candles,
        is_open=is_open,
        phase=phase,
        minutes_to_close=minutes_to_close
    )


def table_count(table_name: str) -> int:
    with database.session() as session:
        row = session.fetchone(f"SELECT COUNT(*) AS count FROM {table_name}")
    return int(row["count"]) if row else 0


def test_health(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_list_opportunities(client: TestClient) -> None:
    response = client.get("/opportunities")

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "render-api"
    assert len(body["items"]) >= 3


def test_alpha_vantage_provider_normalization() -> None:
    def fetch_json(params: dict[str, str]) -> dict[str, object]:
        function = params["function"]
        if function == "GLOBAL_QUOTE":
            return {
                "Global Quote": {
                    "01. symbol": "MSFT",
                    "05. price": "426.50",
                    "07. latest trading day": "2026-04-03",
                    "08. previous close": "421.00",
                    "09. change": "5.50",
                    "10. change percent": "1.3064%"
                }
            }
        if function == "TIME_SERIES_INTRADAY":
            return {
                "Time Series (5min)": {
                    "2026-04-03 15:55:00": {
                        "1. open": "426.10",
                        "2. high": "426.95",
                        "3. low": "425.80",
                        "4. close": "426.80",
                        "5. volume": "320000"
                    },
                    "2026-04-03 15:50:00": {
                        "1. open": "425.60",
                        "2. high": "426.20",
                        "3. low": "425.10",
                        "4. close": "426.10",
                        "5. volume": "301000"
                    }
                }
            }
        if function == "TIME_SERIES_DAILY":
            return {
                "Time Series (Daily)": {
                    "2026-04-03": {
                        "1. open": "423.00",
                        "2. high": "427.10",
                        "3. low": "422.50",
                        "4. close": "426.50",
                        "5. volume": "21000000"
                    },
                    "2026-04-02": {
                        "1. open": "420.00",
                        "2. high": "423.40",
                        "3. low": "419.80",
                        "4. close": "421.00",
                        "5. volume": "18400000"
                    }
                }
            }
        if function == "SYMBOL_SEARCH":
            return {
                "bestMatches": [
                    {
                        "1. symbol": "MSFT",
                        "2. name": "Microsoft Corporation",
                        "3. type": "Equity",
                        "4. region": "United States",
                        "8. currency": "USD",
                        "9. matchScore": "1.0000"
                    }
                ]
            }
        if function == "MARKET_STATUS":
            return {
                "markets": [
                    {
                        "market_type": "Equity",
                        "region": "United States",
                        "local_open": "09:30",
                        "local_close": "16:15",
                        "current_status": "open"
                    }
                ]
            }
        raise AssertionError(f"Unexpected function {function}")

    provider = AlphaVantageMarketDataProvider(
        api_key="test-key",
        timeout_seconds=1,
        fetch_json=fetch_json
    )

    quote = provider.get_quote("msft")
    intraday = provider.get_intraday_candles("msft", "5min", 2)
    daily = provider.get_daily_candles("msft", 2)
    matches = provider.search_symbols("micro", 5)
    clock = provider.get_market_clock()

    assert quote.symbol == "MSFT"
    assert quote.last == 426.5
    assert quote.previous_close == 421.0
    assert quote.quality == "provider"
    assert intraday.interval == "5min"
    assert len(intraday.items) == 2
    assert intraday.items[-1].close == 426.8
    assert len(daily.items) == 2
    assert daily.items[-1].close == 426.5
    assert matches.items[0].symbol == "MSFT"
    assert clock.quality == "provider"
    assert clock.phase in {"premarket", "opening_range", "midday", "power_hour", "near_close", "after_hours", "closed"}
    assert clock.next_open


def test_market_quote_and_candle_retrieval(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_gateway = FakeMarketDataGateway(
        quotes={
            "AAPL": build_quote("AAPL", last=210.0, previous_close=205.0),
            "SPY": build_quote("SPY", last=530.0, previous_close=525.0),
            "QQQ": build_quote("QQQ", last=460.0, previous_close=455.0),
            "IWM": build_quote("IWM", last=210.0, previous_close=208.0)
        },
        candles={
            ("AAPL", "1min"): build_candles("AAPL", [209.1, 209.4, 210.0], interval="1min"),
            ("AAPL", "5min"): build_candles("AAPL", [205 + index for index in range(24)], interval="5min"),
            ("AAPL", "15min"): build_candles("AAPL", [205 + (index * 1.2) for index in range(16)], interval="15min"),
            ("AAPL", "1day"): build_candles("AAPL", [190 + index for index in range(10)]),
            ("SPY", "1min"): build_candles("SPY", [528.4, 529.0, 530.0], interval="1min"),
            ("SPY", "5min"): build_candles("SPY", [520 + index for index in range(24)], interval="5min"),
            ("SPY", "15min"): build_candles("SPY", [520 + (index * 1.1) for index in range(16)], interval="15min"),
            ("SPY", "1day"): build_candles("SPY", [500 + index for index in range(10)]),
            ("QQQ", "1min"): build_candles("QQQ", [458.4, 459.0, 460.0], interval="1min"),
            ("QQQ", "5min"): build_candles("QQQ", [448 + index for index in range(24)], interval="5min"),
            ("QQQ", "15min"): build_candles("QQQ", [448 + (index * 0.9) for index in range(16)], interval="15min"),
            ("QQQ", "1day"): build_candles("QQQ", [430 + index for index in range(10)]),
            ("IWM", "1min"): build_candles("IWM", [208.2, 208.7, 210.0], interval="1min"),
            ("IWM", "5min"): build_candles("IWM", [205 + (index * 0.2) for index in range(24)], interval="5min"),
            ("IWM", "15min"): build_candles("IWM", [205 + (index * 0.25) for index in range(16)], interval="15min"),
            ("IWM", "1day"): build_candles("IWM", [195 + (index * 0.2) for index in range(10)])
        },
        is_open=True,
        phase="midday"
    )
    monkeypatch.setattr(market_service, "get_market_data_gateway", lambda: fake_gateway)

    quote_response = client.get("/market/quotes/AAPL")
    candles_response = client.get("/market/candles/AAPL?interval=5min&limit=10")

    assert quote_response.status_code == 200
    assert quote_response.json()["source"] == "alpha-vantage-1min-close"
    assert quote_response.json()["quality"] == "provider"
    assert candles_response.status_code == 200
    assert len(candles_response.json()["items"]) == 10
    assert candles_response.json()["interval"] == "5min"
    assert candles_response.json()["quality"] == "provider"


def test_dev_fallback_behavior_when_keys_are_absent(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    fallback_gateway = MarketDataGateway(
        primary_provider=None,
        fallback_provider=FallbackMarketDataProvider(),
        allow_fallback=True
    )
    monkeypatch.setattr(market_service, "get_market_data_gateway", lambda: fallback_gateway)

    response = client.get("/market/quotes/TSLA")

    assert response.status_code == 200
    body = response.json()
    assert body["quality"] == "fallback"
    assert body["source"] == "deterministic-1min-candles-1min-close"


def test_signal_generation_uses_provider_backed_market_data(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch
) -> None:
    start_session(client)
    fake_gateway = FakeMarketDataGateway(
        quotes={
            "NVDA": build_quote("NVDA", last=980.0, previous_close=965.0),
            "AAPL": build_quote("AAPL", last=184.0, previous_close=190.0),
            "SPY": build_quote("SPY", last=530.0, previous_close=525.0),
            "QQQ": build_quote("QQQ", last=460.0, previous_close=455.0),
            "IWM": build_quote("IWM", last=209.0, previous_close=207.5)
        },
        candles={
            ("NVDA", "1min"): build_candles("NVDA", [978.4, 979.1, 980.0], interval="1min"),
            ("NVDA", "5min"): build_candles(
                "NVDA",
                [970, 972, 973, 974, 976, 978, 981, 984],
                interval="5min",
                volumes=[120000, 130000, 140000, 150000, 170000, 240000, 260000, 280000]
            ),
            ("NVDA", "15min"): build_candles("NVDA", [965, 968, 971, 975, 979, 983], interval="15min"),
            ("NVDA", "1day"): build_candles("NVDA", [940, 950, 958, 965]),
            ("AAPL", "1min"): build_candles("AAPL", [186.2, 185.1, 184.0], interval="1min"),
            ("AAPL", "5min"): build_candles("AAPL", [191, 190.5, 189.8, 188.9, 187.5, 186.1, 185.0, 184.0], interval="5min"),
            ("AAPL", "15min"): build_candles("AAPL", [194, 192, 190, 188, 186, 184.5], interval="15min"),
            ("AAPL", "1day"): build_candles("AAPL", [198, 195, 192, 190]),
            ("SPY", "1min"): build_candles("SPY", [528.4, 529.2, 530.0], interval="1min"),
            ("SPY", "5min"): build_candles("SPY", [525.2, 525.8, 526.1, 527.0, 528.0, 529.0, 529.5, 530.0], interval="5min"),
            ("SPY", "15min"): build_candles("SPY", [523, 524, 525.2, 526.8, 528.2, 529.4], interval="15min"),
            ("SPY", "1day"): build_candles("SPY", [520, 522, 523, 525]),
            ("QQQ", "1min"): build_candles("QQQ", [458.4, 459.0, 460.0], interval="1min"),
            ("QQQ", "5min"): build_candles("QQQ", [455.2, 456.1, 456.8, 457.5, 458.4, 459.1, 459.4, 460.0], interval="5min"),
            ("QQQ", "15min"): build_candles("QQQ", [452, 453.5, 455.0, 456.8, 458.2, 459.6], interval="15min"),
            ("QQQ", "1day"): build_candles("QQQ", [448, 450, 452, 455]),
            ("IWM", "1min"): build_candles("IWM", [208.2, 208.7, 209.0], interval="1min"),
            ("IWM", "5min"): build_candles("IWM", [206.8, 207.0, 207.2, 207.5, 207.9, 208.3, 208.7, 209.0], interval="5min"),
            ("IWM", "15min"): build_candles("IWM", [205.6, 206.2, 206.9, 207.5, 208.2, 208.9], interval="15min"),
            ("IWM", "1day"): build_candles("IWM", [203, 204, 205, 207.5])
        },
        is_open=True,
        phase="midday"
    )
    monkeypatch.setattr(market_service, "get_market_data_gateway", lambda: fake_gateway)

    response = client.get("/signals")

    assert response.status_code == 200
    body = response.json()
    nvda_signal = signal_by_symbol(body, "NVDA")
    assert body["market_data_quality"] == "provider"
    assert nvda_signal["market_data_quality"] == "provider"
    assert nvda_signal["market_data_source"] == "alpha-vantage-1min-close"
    assert nvda_signal["action"] == "BUY"
    assert nvda_signal["setup_type"] == "opening_range_breakout"


def test_watchlist_and_portfolio_use_provider_pricing(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch
) -> None:
    start_session(client)
    fake_gateway = FakeMarketDataGateway(
        quotes={
            "AAPL": build_quote("AAPL", last=210.0, previous_close=205.0),
            "SPY": build_quote("SPY", last=530.0, previous_close=525.0),
            "QQQ": build_quote("QQQ", last=460.0, previous_close=455.0),
            "IWM": build_quote("IWM", last=210.0, previous_close=208.0),
            "NVDA": build_quote("NVDA", last=980.0, previous_close=965.0)
        },
        candles={
            ("AAPL", "1min"): build_candles("AAPL", [209.1, 209.5, 210.0], interval="1min"),
            ("AAPL", "5min"): build_candles("AAPL", [205 + index for index in range(20)], interval="5min"),
            ("AAPL", "15min"): build_candles("AAPL", [205 + (index * 1.2) for index in range(12)], interval="15min"),
            ("AAPL", "1day"): build_candles("AAPL", [190 + index for index in range(10)]),
            ("SPY", "1min"): build_candles("SPY", [528.4, 529.0, 530.0], interval="1min"),
            ("SPY", "5min"): build_candles("SPY", [520 + index for index in range(20)], interval="5min"),
            ("SPY", "15min"): build_candles("SPY", [520 + (index * 1.1) for index in range(12)], interval="15min"),
            ("SPY", "1day"): build_candles("SPY", [500 + index for index in range(10)]),
            ("QQQ", "1min"): build_candles("QQQ", [458.4, 459.0, 460.0], interval="1min"),
            ("QQQ", "5min"): build_candles("QQQ", [448 + index for index in range(20)], interval="5min"),
            ("QQQ", "15min"): build_candles("QQQ", [448 + (index * 0.9) for index in range(12)], interval="15min"),
            ("QQQ", "1day"): build_candles("QQQ", [430 + index for index in range(10)]),
            ("IWM", "1min"): build_candles("IWM", [208.2, 208.7, 210.0], interval="1min"),
            ("IWM", "5min"): build_candles("IWM", [205 + (index * 0.2) for index in range(20)], interval="5min"),
            ("IWM", "15min"): build_candles("IWM", [205 + (index * 0.25) for index in range(12)], interval="15min"),
            ("IWM", "1day"): build_candles("IWM", [195 + (index * 0.2) for index in range(10)]),
            ("NVDA", "1min"): build_candles("NVDA", [978.2, 979.0, 980.0], interval="1min"),
            ("NVDA", "5min"): build_candles("NVDA", [965 + (index * 1.6) for index in range(20)], interval="5min"),
            ("NVDA", "15min"): build_candles("NVDA", [965 + (index * 2.4) for index in range(12)], interval="15min"),
            ("NVDA", "1day"): build_candles("NVDA", [920 + (index * 10) for index in range(10)])
        },
        is_open=True,
        phase="midday"
    )
    monkeypatch.setattr(market_service, "get_market_data_gateway", lambda: fake_gateway)

    watchlist_create = client.post("/watchlist/items", json={"symbol": "AAPL", "notes": "Provider priced"})
    order_create = client.post("/paper/orders", json={"symbol": "AAPL", "side": "buy", "quantity": 2})

    assert watchlist_create.status_code == 201
    assert order_create.status_code == 201

    watchlist_response = client.get("/watchlist")
    summary_response = client.get("/paper/summary")
    positions_response = client.get("/paper/positions")

    assert watchlist_response.status_code == 200
    assert watchlist_response.json()["items"][0]["quote"]["source"] == "alpha-vantage-1min-close"
    assert summary_response.status_code == 200
    assert summary_response.json()["market_data_source"] == "alpha-vantage-1min-close"
    assert positions_response.status_code == 200
    assert positions_response.json()["items"][0]["market_source"] == "alpha-vantage-1min-close"


def test_opening_range_breakout_logic(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    start_session(client)
    fake_gateway = FakeMarketDataGateway(
        quotes={
            "NVDA": build_quote("NVDA", last=980.0, previous_close=965.0),
            "AAPL": build_quote("AAPL", last=184.0, previous_close=190.0),
            "SPY": build_quote("SPY", last=530.0, previous_close=525.0),
            "QQQ": build_quote("QQQ", last=460.0, previous_close=455.0),
            "IWM": build_quote("IWM", last=209.0, previous_close=207.5)
        },
        candles={
            ("NVDA", "1min"): build_candles("NVDA", [978.8, 979.5, 980.0], interval="1min"),
            ("NVDA", "5min"): build_candles(
                "NVDA",
                [970, 972, 973, 974, 976, 978, 981, 984],
                interval="5min",
                volumes=[120000, 130000, 140000, 150000, 170000, 240000, 260000, 280000]
            ),
            ("NVDA", "15min"): build_candles("NVDA", [965, 968, 971, 975, 979, 983], interval="15min"),
            ("NVDA", "1day"): build_candles("NVDA", [940, 950, 958, 965]),
            ("AAPL", "1min"): build_candles("AAPL", [186.2, 185.1, 184.0], interval="1min"),
            ("AAPL", "5min"): build_candles("AAPL", [191, 190.5, 189.8, 188.9, 187.5, 186.1, 185.0, 184.0], interval="5min"),
            ("AAPL", "15min"): build_candles("AAPL", [194, 192, 190, 188, 186, 184.5], interval="15min"),
            ("AAPL", "1day"): build_candles("AAPL", [198, 195, 192, 190]),
            ("SPY", "1min"): build_candles("SPY", [528.4, 529.2, 530.0], interval="1min"),
            ("SPY", "5min"): build_candles("SPY", [525.2, 525.8, 526.1, 527.0, 528.0, 529.0, 529.5, 530.0], interval="5min"),
            ("SPY", "15min"): build_candles("SPY", [523, 524, 525.2, 526.8, 528.2, 529.4], interval="15min"),
            ("SPY", "1day"): build_candles("SPY", [520, 522, 523, 525]),
            ("QQQ", "1min"): build_candles("QQQ", [458.4, 459.0, 460.0], interval="1min"),
            ("QQQ", "5min"): build_candles("QQQ", [455.2, 456.1, 456.8, 457.5, 458.4, 459.1, 459.4, 460.0], interval="5min"),
            ("QQQ", "15min"): build_candles("QQQ", [452, 453.5, 455.0, 456.8, 458.2, 459.6], interval="15min"),
            ("QQQ", "1day"): build_candles("QQQ", [448, 450, 452, 455]),
            ("IWM", "1min"): build_candles("IWM", [208.2, 208.7, 209.0], interval="1min"),
            ("IWM", "5min"): build_candles("IWM", [206.8, 207.0, 207.2, 207.5, 207.9, 208.3, 208.7, 209.0], interval="5min"),
            ("IWM", "15min"): build_candles("IWM", [205.6, 206.2, 206.9, 207.5, 208.2, 208.9], interval="15min"),
            ("IWM", "1day"): build_candles("IWM", [203, 204, 205, 207.5])
        },
        is_open=True,
        phase="midday"
    )
    monkeypatch.setattr(market_service, "get_market_data_gateway", lambda: fake_gateway)

    response = client.get("/signals")

    assert response.status_code == 200
    body = response.json()
    nvda_signal = signal_by_symbol(body, "NVDA")

    assert nvda_signal["action"] == "BUY"
    assert nvda_signal["setup_type"] == "opening_range_breakout"
    assert nvda_signal["entry_state"] == "enter_now"
    assert nvda_signal["trigger_price"] > 0
    assert nvda_signal["stop_loss"] < nvda_signal["entry_price"]
    assert any(alert["type"] == "new_actionable_setup" for alert in body["alerts"])


def test_vwap_reclaim_logic() -> None:
    quote = build_quote("MSFT", last=426.4, previous_close=421.0)
    execution_bars = build_candles(
        "MSFT",
        [426.1, 425.8, 425.2, 424.9, 425.3, 425.7, 426.0, 426.4],
        interval="5min",
        volumes=[120000, 110000, 105000, 115000, 140000, 180000, 210000, 240000]
    ).items
    confirmation_bars = build_candles(
        "MSFT",
        [424.9, 425.0, 425.2, 425.4, 425.8, 426.2],
        interval="15min"
    ).items
    context = SignalContext(
        symbol="MSFT",
        quote=quote,
        features=IntradayFeatureBundle(
            snapshot=IntradayFeatureSnapshot(
                execution_interval="5min",
                confirmation_interval="15min",
                session_phase="midday",
                opening_range_high=426.95,
                opening_range_low=424.95,
                session_high=426.95,
                session_low=424.7,
                vwap=425.84,
                momentum_5m_pct=0.19,
                momentum_15m_pct=0.21,
                pullback_depth_pct=0.31,
                relative_volume=1.42,
                session_range_pct=0.53,
                trend_alignment="bullish",
                breakout_state="inside_range",
                distance_to_stop_pct=None
            ),
            execution_bars=execution_bars,
            confirmation_bars=confirmation_bars
        ),
        watchlist_item=None,
        position=None,
        market_overview=MarketOverviewResponse(
            as_of=datetime.now(timezone.utc),
            source="test",
            quality="provider",
            clock=MarketClock(
                is_open=True,
                session="regular",
                phase="midday",
                as_of=datetime.now(timezone.utc),
                next_open="2026-04-06 09:30 ET",
                next_close="2026-04-06 16:00 ET",
                minutes_since_open=90,
                minutes_to_close=240,
                source="test",
                quality="provider"
            ),
            regime=MarketRegime(
                headline="Constructive intraday tape",
                summary="Breadth is supportive.",
                volatility_regime="Normal range",
                breadth_regime="Benchmarks are supportive."
            ),
            benchmarks=[],
            highlights=[],
            upcoming_events=[]
        ),
        market_clock=MarketClock(
            is_open=True,
            session="regular",
            phase="midday",
            as_of=datetime.now(timezone.utc),
            next_open="2026-04-06 09:30 ET",
            next_close="2026-04-06 16:00 ET",
            minutes_since_open=90,
            minutes_to_close=240,
            source="test",
            quality="provider"
        ),
        risk_snapshot=RiskSnapshot(
            execution_mode="paper",
            entitlement="paper",
            metrics=[],
            concentration=[ExposureBucket(bucket="Tech", value=20)]
        ),
        portfolio=SignalPortfolioState(
            capital_base=100000,
            gross_exposure=0,
            gross_exposure_pct=0,
            available_exposure_pct=40,
            max_total_exposure_pct=40,
            max_risk_per_trade_pct=0.4,
            max_daily_loss_pct=1.5,
            max_open_positions=4,
            max_symbol_concentration_pct=18,
            open_positions=0,
            risk_utilization_pct=0,
            daily_pnl=0,
            daily_pnl_pct=0,
            daily_loss_limit_hit=False,
            flatten_before_close=False,
            warnings=[]
        )
    )

    candidate = RuleBasedIntradaySignalEngine()._vwap_reclaim(context)

    assert candidate.setup_type == "vwap_reclaim"
    assert candidate.action == "BUY"
    assert candidate.entry_state == "enter_now"
    assert candidate.stop_loss is not None
    assert candidate.take_profit1 is not None


def test_no_trade_case_for_chop(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    start_session(client)
    watchlist_response = client.post("/watchlist/items", json={"symbol": "IBM", "notes": "Needs a cleaner setup"})
    assert watchlist_response.status_code == 201

    fake_gateway = FakeMarketDataGateway(
        quotes={
            "IBM": build_quote("IBM", last=182.0, previous_close=181.95),
            "SPY": build_quote("SPY", last=530.0, previous_close=525.0),
            "QQQ": build_quote("QQQ", last=460.0, previous_close=455.0),
            "IWM": build_quote("IWM", last=209.0, previous_close=207.5),
            "NVDA": build_quote("NVDA", last=970.0, previous_close=965.0),
            "AAPL": build_quote("AAPL", last=184.0, previous_close=190.0)
        },
        candles={
            ("IBM", "1min"): build_candles("IBM", [182.02, 182.01, 182.0], interval="1min"),
            ("IBM", "5min"): build_candles("IBM", [182.18, 182.22, 182.2, 182.12, 182.1, 182.08, 182.05, 182.0], interval="5min", volumes=[100000] * 8),
            ("IBM", "15min"): build_candles("IBM", [182.16, 182.15, 182.13, 182.12, 182.1, 182.08], interval="15min", volumes=[200000] * 6),
            ("IBM", "1day"): build_candles("IBM", [181.7, 181.85, 181.9, 181.95]),
            ("SPY", "1min"): build_candles("SPY", [528.4, 529.2, 530.0], interval="1min"),
            ("SPY", "5min"): build_candles("SPY", [525.2, 525.8, 526.1, 527.0, 528.0, 529.0, 529.5, 530.0], interval="5min"),
            ("SPY", "15min"): build_candles("SPY", [523, 524, 525.2, 526.8, 528.2, 529.4], interval="15min"),
            ("SPY", "1day"): build_candles("SPY", [520, 522, 523, 525]),
            ("QQQ", "1min"): build_candles("QQQ", [458.4, 459.0, 460.0], interval="1min"),
            ("QQQ", "5min"): build_candles("QQQ", [455.2, 456.1, 456.8, 457.5, 458.4, 459.1, 459.4, 460.0], interval="5min"),
            ("QQQ", "15min"): build_candles("QQQ", [452, 453.5, 455.0, 456.8, 458.2, 459.6], interval="15min"),
            ("QQQ", "1day"): build_candles("QQQ", [448, 450, 452, 455]),
            ("IWM", "1min"): build_candles("IWM", [208.2, 208.7, 209.0], interval="1min"),
            ("IWM", "5min"): build_candles("IWM", [206.8, 207.0, 207.2, 207.5, 207.9, 208.3, 208.7, 209.0], interval="5min"),
            ("IWM", "15min"): build_candles("IWM", [205.6, 206.2, 206.9, 207.5, 208.2, 208.9], interval="15min"),
            ("IWM", "1day"): build_candles("IWM", [203, 204, 205, 207.5]),
            ("NVDA", "1min"): build_candles("NVDA", [968.8, 969.5, 970.0], interval="1min"),
            ("NVDA", "5min"): build_candles("NVDA", [965 + (index * 0.8) for index in range(8)], interval="5min"),
            ("NVDA", "15min"): build_candles("NVDA", [965 + (index * 1.1) for index in range(6)], interval="15min"),
            ("NVDA", "1day"): build_candles("NVDA", [950, 955, 960, 965]),
            ("AAPL", "1min"): build_candles("AAPL", [186.2, 185.1, 184.0], interval="1min"),
            ("AAPL", "5min"): build_candles("AAPL", [191, 190.5, 189.8, 188.9, 187.5, 186.1, 185.0, 184.0], interval="5min"),
            ("AAPL", "15min"): build_candles("AAPL", [194, 192, 190, 188, 186, 184.5], interval="15min"),
            ("AAPL", "1day"): build_candles("AAPL", [198, 195, 192, 190])
        },
        is_open=True,
        phase="midday"
    )
    monkeypatch.setattr(market_service, "get_market_data_gateway", lambda: fake_gateway)

    response = client.get("/signals")

    assert response.status_code == 200
    body = response.json()
    ibm_signal = signal_by_symbol(body, "IBM")

    assert ibm_signal["action"] == "NO_TRADE"
    assert ibm_signal["is_actionable"] is False
    assert ibm_signal["entry_state"] in {"stand_aside", "wait_for_confirmation"}
    assert "wait" in ibm_signal["thesis"].lower() or "stand aside" in ibm_signal["thesis"].lower()


def test_risk_based_sizing_for_intraday_stops(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    start_session(client)
    fake_gateway = FakeMarketDataGateway(
        quotes={
            "NVDA": build_quote("NVDA", last=980.0, previous_close=965.0),
            "AAPL": build_quote("AAPL", last=184.0, previous_close=190.0),
            "SPY": build_quote("SPY", last=530.0, previous_close=525.0),
            "QQQ": build_quote("QQQ", last=460.0, previous_close=455.0),
            "IWM": build_quote("IWM", last=209.0, previous_close=207.5)
        },
        candles={
            ("NVDA", "1min"): build_candles("NVDA", [978.8, 979.5, 980.0], interval="1min"),
            ("NVDA", "5min"): build_candles(
                "NVDA",
                [970, 972, 973, 974, 976, 978, 981, 984],
                interval="5min",
                volumes=[120000, 130000, 140000, 150000, 170000, 240000, 260000, 280000]
            ),
            ("NVDA", "15min"): build_candles("NVDA", [965, 968, 971, 975, 979, 983], interval="15min"),
            ("NVDA", "1day"): build_candles("NVDA", [940, 950, 958, 965]),
            ("AAPL", "1min"): build_candles("AAPL", [186.2, 185.1, 184.0], interval="1min"),
            ("AAPL", "5min"): build_candles("AAPL", [191, 190.5, 189.8, 188.9, 187.5, 186.1, 185.0, 184.0], interval="5min"),
            ("AAPL", "15min"): build_candles("AAPL", [194, 192, 190, 188, 186, 184.5], interval="15min"),
            ("AAPL", "1day"): build_candles("AAPL", [198, 195, 192, 190]),
            ("SPY", "1min"): build_candles("SPY", [528.4, 529.2, 530.0], interval="1min"),
            ("SPY", "5min"): build_candles("SPY", [525.2, 525.8, 526.1, 527.0, 528.0, 529.0, 529.5, 530.0], interval="5min"),
            ("SPY", "15min"): build_candles("SPY", [523, 524, 525.2, 526.8, 528.2, 529.4], interval="15min"),
            ("SPY", "1day"): build_candles("SPY", [520, 522, 523, 525]),
            ("QQQ", "1min"): build_candles("QQQ", [458.4, 459.0, 460.0], interval="1min"),
            ("QQQ", "5min"): build_candles("QQQ", [455.2, 456.1, 456.8, 457.5, 458.4, 459.1, 459.4, 460.0], interval="5min"),
            ("QQQ", "15min"): build_candles("QQQ", [452, 453.5, 455.0, 456.8, 458.2, 459.6], interval="15min"),
            ("QQQ", "1day"): build_candles("QQQ", [448, 450, 452, 455]),
            ("IWM", "1min"): build_candles("IWM", [208.2, 208.7, 209.0], interval="1min"),
            ("IWM", "5min"): build_candles("IWM", [206.8, 207.0, 207.2, 207.5, 207.9, 208.3, 208.7, 209.0], interval="5min"),
            ("IWM", "15min"): build_candles("IWM", [205.6, 206.2, 206.9, 207.5, 208.2, 208.9], interval="15min"),
            ("IWM", "1day"): build_candles("IWM", [203, 204, 205, 207.5])
        },
        is_open=True,
        phase="midday"
    )
    monkeypatch.setattr(market_service, "get_market_data_gateway", lambda: fake_gateway)

    response = client.get("/signals")

    assert response.status_code == 200
    nvda_signal = signal_by_symbol(response.json(), "NVDA")
    stop_distance_pct = ((nvda_signal["entry_price"] - nvda_signal["stop_loss"]) / nvda_signal["entry_price"]) * 100
    max_size_from_risk = (0.4 * 100) / stop_distance_pct

    assert nvda_signal["position_size_pct"] <= 12
    assert nvda_signal["position_size_pct"] <= max_size_from_risk + 0.5


def test_time_based_exit_behavior(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    start_session(client)
    fake_gateway = FakeMarketDataGateway(
        quotes={
            "NVDA": build_quote("NVDA", last=980.0, previous_close=965.0),
            "AAPL": build_quote("AAPL", last=184.0, previous_close=190.0),
            "SPY": build_quote("SPY", last=530.0, previous_close=525.0),
            "QQQ": build_quote("QQQ", last=460.0, previous_close=455.0),
            "IWM": build_quote("IWM", last=209.0, previous_close=207.5)
        },
        candles={
            ("NVDA", "1min"): build_candles("NVDA", [978.8, 979.5, 980.0], interval="1min"),
            ("NVDA", "5min"): build_candles("NVDA", [970, 972, 973, 974, 976, 978, 981, 984], interval="5min"),
            ("NVDA", "15min"): build_candles("NVDA", [965, 968, 971, 975, 979, 983], interval="15min"),
            ("NVDA", "1day"): build_candles("NVDA", [940, 950, 958, 965]),
            ("AAPL", "1min"): build_candles("AAPL", [186.2, 185.1, 184.0], interval="1min"),
            ("AAPL", "5min"): build_candles("AAPL", [191, 190.5, 189.8, 188.9, 187.5, 186.1, 185.0, 184.0], interval="5min"),
            ("AAPL", "15min"): build_candles("AAPL", [194, 192, 190, 188, 186, 184.5], interval="15min"),
            ("AAPL", "1day"): build_candles("AAPL", [198, 195, 192, 190]),
            ("SPY", "1min"): build_candles("SPY", [528.4, 529.2, 530.0], interval="1min"),
            ("SPY", "5min"): build_candles("SPY", [525.2, 525.8, 526.1, 527.0, 528.0, 529.0, 529.5, 530.0], interval="5min"),
            ("SPY", "15min"): build_candles("SPY", [523, 524, 525.2, 526.8, 528.2, 529.4], interval="15min"),
            ("SPY", "1day"): build_candles("SPY", [520, 522, 523, 525]),
            ("QQQ", "1min"): build_candles("QQQ", [458.4, 459.0, 460.0], interval="1min"),
            ("QQQ", "5min"): build_candles("QQQ", [455.2, 456.1, 456.8, 457.5, 458.4, 459.1, 459.4, 460.0], interval="5min"),
            ("QQQ", "15min"): build_candles("QQQ", [452, 453.5, 455.0, 456.8, 458.2, 459.6], interval="15min"),
            ("QQQ", "1day"): build_candles("QQQ", [448, 450, 452, 455]),
            ("IWM", "1min"): build_candles("IWM", [208.2, 208.7, 209.0], interval="1min"),
            ("IWM", "5min"): build_candles("IWM", [206.8, 207.0, 207.2, 207.5, 207.9, 208.3, 208.7, 209.0], interval="5min"),
            ("IWM", "15min"): build_candles("IWM", [205.6, 206.2, 206.9, 207.5, 208.2, 208.9], interval="15min"),
            ("IWM", "1day"): build_candles("IWM", [203, 204, 205, 207.5])
        },
        is_open=True,
        phase="near_close",
        minutes_to_close=12
    )
    monkeypatch.setattr(market_service, "get_market_data_gateway", lambda: fake_gateway)

    buy_response = client.post("/paper/orders", json={"symbol": "NVDA", "side": "buy", "quantity": 1})
    assert buy_response.status_code == 201

    response = client.get("/signals")

    assert response.status_code == 200
    body = response.json()
    nvda_signal = signal_by_symbol(body, "NVDA")

    assert nvda_signal["action"] == "EXIT"
    assert nvda_signal["has_position"] is True
    assert "close" in nvda_signal["thesis"].lower()


def test_intraday_signal_explanation_shape(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    start_session(client)
    fake_gateway = FakeMarketDataGateway(
        quotes={
            "NVDA": build_quote("NVDA", last=980.0, previous_close=965.0),
            "AAPL": build_quote("AAPL", last=184.0, previous_close=190.0),
            "SPY": build_quote("SPY", last=530.0, previous_close=525.0),
            "QQQ": build_quote("QQQ", last=460.0, previous_close=455.0),
            "IWM": build_quote("IWM", last=209.0, previous_close=207.5)
        },
        candles={
            ("NVDA", "1min"): build_candles("NVDA", [978.8, 979.5, 980.0], interval="1min"),
            ("NVDA", "5min"): build_candles(
                "NVDA",
                [970, 972, 973, 974, 976, 978, 981, 984],
                interval="5min",
                volumes=[120000, 130000, 140000, 150000, 170000, 240000, 260000, 280000]
            ),
            ("NVDA", "15min"): build_candles("NVDA", [965, 968, 971, 975, 979, 983], interval="15min"),
            ("NVDA", "1day"): build_candles("NVDA", [940, 950, 958, 965]),
            ("AAPL", "1min"): build_candles("AAPL", [186.2, 185.1, 184.0], interval="1min"),
            ("AAPL", "5min"): build_candles("AAPL", [191, 190.5, 189.8, 188.9, 187.5, 186.1, 185.0, 184.0], interval="5min"),
            ("AAPL", "15min"): build_candles("AAPL", [194, 192, 190, 188, 186, 184.5], interval="15min"),
            ("AAPL", "1day"): build_candles("AAPL", [198, 195, 192, 190]),
            ("SPY", "1min"): build_candles("SPY", [528.4, 529.2, 530.0], interval="1min"),
            ("SPY", "5min"): build_candles("SPY", [525.2, 525.8, 526.1, 527.0, 528.0, 529.0, 529.5, 530.0], interval="5min"),
            ("SPY", "15min"): build_candles("SPY", [523, 524, 525.2, 526.8, 528.2, 529.4], interval="15min"),
            ("SPY", "1day"): build_candles("SPY", [520, 522, 523, 525]),
            ("QQQ", "1min"): build_candles("QQQ", [458.4, 459.0, 460.0], interval="1min"),
            ("QQQ", "5min"): build_candles("QQQ", [455.2, 456.1, 456.8, 457.5, 458.4, 459.1, 459.4, 460.0], interval="5min"),
            ("QQQ", "15min"): build_candles("QQQ", [452, 453.5, 455.0, 456.8, 458.2, 459.6], interval="15min"),
            ("QQQ", "1day"): build_candles("QQQ", [448, 450, 452, 455]),
            ("IWM", "1min"): build_candles("IWM", [208.2, 208.7, 209.0], interval="1min"),
            ("IWM", "5min"): build_candles("IWM", [206.8, 207.0, 207.2, 207.5, 207.9, 208.3, 208.7, 209.0], interval="5min"),
            ("IWM", "15min"): build_candles("IWM", [205.6, 206.2, 206.9, 207.5, 208.2, 208.9], interval="15min"),
            ("IWM", "1day"): build_candles("IWM", [203, 204, 205, 207.5])
        },
        is_open=True,
        phase="midday"
    )
    monkeypatch.setattr(market_service, "get_market_data_gateway", lambda: fake_gateway)

    response = client.get("/signals")

    assert response.status_code == 200
    body = response.json()
    focus = body["focus"]
    nvda_signal = signal_by_symbol(body, "NVDA")

    assert focus["headline"]
    assert len(focus["next_steps"]) >= 2
    assert nvda_signal["strategy_type"] == "Opening range breakout"
    assert nvda_signal["entry_state"] == "enter_now"
    assert nvda_signal["trigger_price"] > 0
    assert "opening range" in nvda_signal["thesis"].lower()
    assert "invalidate" in nvda_signal["invalidation"].lower()
    assert nvda_signal["intraday_features"]["execution_interval"] == "5min"
    assert len(nvda_signal["entry_rules"]) >= 3
    assert len(nvda_signal["exit_rules"]) >= 3


def test_session_creation_and_lookup(client: TestClient) -> None:
    anonymous_response = client.get("/session")

    assert anonymous_response.status_code == 200
    anonymous_body = anonymous_response.json()
    assert anonymous_body["is_authenticated"] is False
    assert anonymous_body["mode"] == "anonymous"
    assert anonymous_body["session_strategy"] == settings.session_strategy

    created_response = client.post(
        "/session",
        json={"handle": "operator-1", "display_name": "Operator One"}
    )

    assert created_response.status_code == 201
    assert "HttpOnly" in (created_response.headers.get("set-cookie") or "")
    created_body = created_response.json()
    assert created_body["is_authenticated"] is True
    assert created_body["user"]["handle"] == "operator-1"

    lookup_response = client.get("/session")

    assert lookup_response.status_code == 200
    lookup_body = lookup_response.json()
    assert lookup_body["is_authenticated"] is True
    assert lookup_body["user"]["name"] == "Operator One"
    assert lookup_body["mode"] == "development"


def test_logout(client: TestClient) -> None:
    start_session(client)

    response = client.post("/session/logout")

    assert response.status_code == 200
    assert response.json()["is_authenticated"] is False

    follow_up = client.get("/session")

    assert follow_up.status_code == 200
    assert follow_up.json()["is_authenticated"] is False


def test_invalid_and_expired_session_behavior(client: TestClient) -> None:
    client.cookies.set(settings.session_cookie_name, "bogus-token")

    invalid_lookup = client.get("/session")

    assert invalid_lookup.status_code == 200
    assert invalid_lookup.json()["is_authenticated"] is False

    start_session(client, handle="expiry-user", display_name="Expiry User")
    with database.session() as session:
        session.execute(
            """
            UPDATE sessions
            SET expires_at = :expires_at
            """,
            {"expires_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()}
        )

    expired_lookup = client.get("/session")

    assert expired_lookup.status_code == 200
    assert expired_lookup.json()["is_authenticated"] is False

    protected_response = client.get("/watchlist")

    assert protected_response.status_code == 401
    assert protected_response.json()["error"]["code"] == "unauthenticated"


def test_watchlist_add_remove_list(client: TestClient) -> None:
    start_session(client)

    empty_response = client.get("/watchlist")

    assert empty_response.status_code == 200
    assert empty_response.json()["items"] == []

    create_response = client.post(
        "/watchlist/items",
        json={"symbol": "nvda", "notes": "AI leader"}
    )

    assert create_response.status_code == 201
    created_item = create_response.json()
    assert created_item["symbol"] == "NVDA"
    assert created_item["notes"] == "AI leader"
    assert created_item["quote"]["last"] > 0

    list_response = client.get("/watchlist")

    assert list_response.status_code == 200
    items = list_response.json()["items"]
    assert len(items) == 1
    assert items[0]["symbol"] == "NVDA"

    delete_response = client.delete("/watchlist/items/NVDA")

    assert delete_response.status_code == 200
    assert delete_response.json()["removed"] is True

    final_response = client.get("/watchlist")

    assert final_response.status_code == 200
    assert final_response.json()["items"] == []


def test_user_scoping_across_watchlist_and_paper_trading() -> None:
    with TestClient(app) as alice_client, TestClient(app) as bob_client:
        start_session(alice_client, handle="alice", display_name="Alice")
        start_session(bob_client, handle="bob", display_name="Bob")

        alice_watchlist = alice_client.post(
            "/watchlist/items",
            json={"symbol": "AAPL", "notes": "Alice watch"}
        )
        assert alice_watchlist.status_code == 201

        alice_order = alice_client.post(
            "/paper/orders",
            json={"symbol": "AAPL", "side": "buy", "quantity": 3}
        )
        assert alice_order.status_code == 201

        bob_watchlist = bob_client.get("/watchlist")
        bob_positions = bob_client.get("/paper/positions")

        assert bob_watchlist.status_code == 200
        assert bob_watchlist.json()["items"] == []
        assert bob_positions.status_code == 200
        assert bob_positions.json()["items"] == []

        alice_watchlist_after = alice_client.get("/watchlist")
        alice_positions_after = alice_client.get("/paper/positions")

        assert len(alice_watchlist_after.json()["items"]) == 1
        assert len(alice_positions_after.json()["items"]) == 1


def test_place_paper_order(client: TestClient) -> None:
    start_session(client)

    response = client.post(
        "/paper/orders",
        json={"symbol": "AAPL", "side": "buy", "quantity": 5}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["order"]["status"] == "filled"
    assert body["fill"]["fill_price"] > body["fill"]["market_price"]
    assert body["position"]["quantity"] == 5


def test_position_updates_after_buy_sell(client: TestClient) -> None:
    start_session(client)

    buy_response = client.post(
        "/paper/orders",
        json={"symbol": "AAPL", "side": "buy", "quantity": 10}
    )
    assert buy_response.status_code == 201

    sell_response = client.post(
        "/paper/orders",
        json={"symbol": "AAPL", "side": "sell", "quantity": 4}
    )

    assert sell_response.status_code == 201
    positions_response = client.get("/paper/positions")
    assert positions_response.status_code == 200

    items = positions_response.json()["items"]
    assert len(items) == 1
    assert items[0]["symbol"] == "AAPL"
    assert items[0]["quantity"] == 6
    assert items[0]["realized_pnl"] < 0


def test_portfolio_summary(client: TestClient) -> None:
    start_session(client)

    order_response = client.post(
        "/paper/orders",
        json={"symbol": "NVDA", "side": "buy", "quantity": 2}
    )
    assert order_response.status_code == 201

    summary_response = client.get("/paper/summary")

    assert summary_response.status_code == 200
    body = summary_response.json()
    assert body["positions"] == 1
    assert body["market_value"] > 0
    assert body["cost_basis"] > body["market_value"]
    assert body["unrealized_pnl"] < 0
    assert body["assumptions"]["sells_require_existing_position"] is True


def test_invalid_order_returns_error_and_records_rejection(client: TestClient) -> None:
    start_session(client)

    response = client.post(
        "/paper/orders",
        json={"symbol": "SPY", "side": "sell", "quantity": 1}
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "insufficient_position"

    orders_response = client.get("/paper/orders")

    assert orders_response.status_code == 200
    orders = orders_response.json()["items"]
    assert len(orders) == 1
    assert orders[0]["status"] == "rejected"
    assert orders[0]["rejection_reason"] == "insufficient_position"


def test_migration_path(tmp_path: Path) -> None:
    migration_database = Database(f"sqlite:///{(tmp_path / 'migration-test.db').as_posix()}")
    manager = MigrationManager(migration_database)

    applied = manager.apply_pending()

    assert applied == [
        "0001_phase2_persistence",
        "0002_phase3_sessions_and_audit",
        "0003_signal_tracking"
    ]
    assert manager.pending() == []

    with migration_database.session() as session:
        tables = {
            row["name"]
            for row in session.fetchall(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert "schema_migrations" in tables
        assert "watchlists" in tables
        assert "paper_orders" in tables
        assert "users" in tables
        assert "sessions" in tables
        assert "audit_events" in tables
        assert "signal_snapshots" in tables
        assert "signal_alerts" in tables


def test_database_error_returns_safe_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch
) -> None:
    start_session(client)

    def raise_database_error(_: WatchlistRepository, user_id: str):
        raise DatabaseError()

    monkeypatch.setattr(WatchlistRepository, "list_items", raise_database_error)

    response = client.get("/watchlist")

    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "database_unavailable"
    assert "Database access" in body["error"]["message"]


def test_signal_snapshot_persistence(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    start_session(client)
    monkeypatch.setattr(market_service, "get_market_data_gateway", lambda: build_signal_gateway())

    response = client.get("/signals")

    assert response.status_code == 200
    assert table_count("signal_snapshots") == 5

    history_response = client.get("/signals/history/NVDA?limit=5")

    assert history_response.status_code == 200
    body = history_response.json()
    assert body["symbol"] == "NVDA"
    assert len(body["items"]) >= 1
    assert body["items"][0]["snapshot_id"]
    assert body["items"][0]["market_phase"] == "midday"


def test_signal_transition_detection_and_new_actionable_alert(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch
) -> None:
    start_session(client)
    closed_gateway = build_signal_gateway(is_open=False, phase="closed", minutes_to_close=None)
    live_gateway = build_signal_gateway()

    monkeypatch.setattr(market_service, "get_market_data_gateway", lambda: closed_gateway)
    first_response = client.get("/signals")
    assert first_response.status_code == 200

    monkeypatch.setattr(market_service, "get_market_data_gateway", lambda: live_gateway)
    second_response = client.get("/signals")
    assert second_response.status_code == 200

    history_response = client.get("/signals/history/NVDA?limit=5")
    alerts_response = client.get("/signals/alerts?minutes=240")

    assert history_response.status_code == 200
    latest_snapshot = history_response.json()["items"][0]
    change_types = {change["type"] for change in latest_snapshot["transition"]["changes"]}
    assert "new_actionable_setup" in change_types
    assert "action_changed" in change_types

    assert alerts_response.status_code == 200
    alert_types = {item["type"] for item in alerts_response.json()["items"]}
    assert "new_actionable_setup" in alert_types


def test_duplicate_alert_suppression(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    start_session(client)
    gateway = build_signal_gateway()
    monkeypatch.setattr(market_service, "get_market_data_gateway", lambda: gateway)

    first_response = client.get("/signals")
    assert first_response.status_code == 200
    first_alert_count = table_count("signal_alerts")

    second_response = client.get("/signals")
    assert second_response.status_code == 200
    second_alert_count = table_count("signal_alerts")

    assert first_alert_count > 0
    assert second_alert_count == first_alert_count


def test_exit_and_stop_alert_generation(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    start_session(client)
    monkeypatch.setattr(market_service, "get_market_data_gateway", lambda: build_signal_gateway())

    initial_signal_response = client.get("/signals")
    assert initial_signal_response.status_code == 200

    buy_response = client.post("/paper/orders", json={"symbol": "NVDA", "side": "buy", "quantity": 1})
    assert buy_response.status_code == 201

    exit_gateway = build_signal_gateway(
        quote_overrides={"NVDA": (940.0, 965.0)},
        candle_overrides={
            ("NVDA", "1min"): build_candles("NVDA", [952.0, 946.5, 940.0], interval="1min"),
            ("NVDA", "5min"): build_candles("NVDA", [980, 978, 975, 970, 962, 954, 947, 940], interval="5min"),
            ("NVDA", "15min"): build_candles("NVDA", [985, 978, 968, 958, 948, 940], interval="15min")
        }
    )
    monkeypatch.setattr(market_service, "get_market_data_gateway", lambda: exit_gateway)

    response = client.get("/signals")
    alerts_response = client.get("/signals/alerts?minutes=240")

    assert response.status_code == 200
    nvda_signal = signal_by_symbol(response.json(), "NVDA")
    assert nvda_signal["action"] == "EXIT"

    assert alerts_response.status_code == 200
    alert_types = {item["type"] for item in alerts_response.json()["items"] if item["symbol"] == "NVDA"}
    assert "exit_signal" in alert_types
    assert "stop_breach" in alert_types


def test_target_hit_alert_generation(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    start_session(client)
    monkeypatch.setattr(market_service, "get_market_data_gateway", lambda: build_signal_gateway())

    initial_signal_response = client.get("/signals")
    assert initial_signal_response.status_code == 200

    buy_response = client.post("/paper/orders", json={"symbol": "NVDA", "side": "buy", "quantity": 1})
    assert buy_response.status_code == 201

    target_gateway = build_signal_gateway(
        quote_overrides={"NVDA": (1006.0, 965.0)},
        candle_overrides={
            ("NVDA", "1min"): build_candles("NVDA", [1001.0, 1004.2, 1006.0], interval="1min"),
            ("NVDA", "5min"): build_candles(
                "NVDA",
                [970, 972, 973, 978, 985, 992, 999, 1006],
                interval="5min",
                volumes=[120000, 130000, 140000, 160000, 200000, 240000, 260000, 300000]
            ),
            ("NVDA", "15min"): build_candles("NVDA", [965, 970, 976, 984, 992, 1000], interval="15min")
        }
    )
    monkeypatch.setattr(market_service, "get_market_data_gateway", lambda: target_gateway)

    response = client.get("/signals")
    alerts_response = client.get("/signals/alerts?minutes=240")

    assert response.status_code == 200
    nvda_signal = signal_by_symbol(response.json(), "NVDA")
    assert nvda_signal["action"] in {"REDUCE", "HOLD"}

    assert alerts_response.status_code == 200
    alert_types = {item["type"] for item in alerts_response.json()["items"] if item["symbol"] == "NVDA"}
    assert "target_hit" in alert_types


def test_near_close_flatten_alert_behavior(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    start_session(client)
    monkeypatch.setattr(market_service, "get_market_data_gateway", lambda: build_signal_gateway())

    initial_signal_response = client.get("/signals")
    assert initial_signal_response.status_code == 200

    buy_response = client.post("/paper/orders", json={"symbol": "NVDA", "side": "buy", "quantity": 1})
    assert buy_response.status_code == 201

    near_close_gateway = build_signal_gateway(
        phase="near_close",
        minutes_to_close=12,
        quote_overrides={"NVDA": (984.0, 965.0)},
        candle_overrides={
            ("NVDA", "1min"): build_candles("NVDA", [982.6, 983.1, 984.0], interval="1min"),
            ("NVDA", "5min"): build_candles("NVDA", [970, 972, 973, 976, 978, 980, 982, 984], interval="5min"),
            ("NVDA", "15min"): build_candles("NVDA", [965, 968, 971, 975, 979, 983], interval="15min")
        }
    )
    monkeypatch.setattr(market_service, "get_market_data_gateway", lambda: near_close_gateway)

    response = client.get("/signals")
    alerts_response = client.get("/signals/alerts?minutes=240")

    assert response.status_code == 200
    nvda_signal = signal_by_symbol(response.json(), "NVDA")
    assert nvda_signal["action"] == "EXIT"

    assert alerts_response.status_code == 200
    alert_types = {item["type"] for item in alerts_response.json()["items"] if item["symbol"] == "NVDA"}
    assert "near_close_flatten_warning" in alert_types


def test_scorecard_generation(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    start_session(client)
    closed_gateway = build_signal_gateway(is_open=False, phase="closed", minutes_to_close=None)
    live_gateway = build_signal_gateway()
    target_gateway = build_signal_gateway(
        quote_overrides={"NVDA": (1006.0, 965.0)},
        candle_overrides={
            ("NVDA", "1min"): build_candles("NVDA", [1001.0, 1004.2, 1006.0], interval="1min"),
            ("NVDA", "5min"): build_candles(
                "NVDA",
                [970, 972, 973, 978, 985, 992, 999, 1006],
                interval="5min",
                volumes=[120000, 130000, 140000, 160000, 200000, 240000, 260000, 300000]
            ),
            ("NVDA", "15min"): build_candles("NVDA", [965, 970, 976, 984, 992, 1000], interval="15min")
        }
    )

    monkeypatch.setattr(market_service, "get_market_data_gateway", lambda: closed_gateway)
    first_response = client.get("/signals")
    assert first_response.status_code == 200

    monkeypatch.setattr(market_service, "get_market_data_gateway", lambda: live_gateway)
    second_response = client.get("/signals")
    assert second_response.status_code == 200

    buy_response = client.post("/paper/orders", json={"symbol": "NVDA", "side": "buy", "quantity": 1})
    assert buy_response.status_code == 201

    monkeypatch.setattr(market_service, "get_market_data_gateway", lambda: target_gateway)
    third_response = client.get("/signals")
    assert third_response.status_code == 200

    scorecard_response = client.get("/signals/scorecard?lookback_days=1")

    assert scorecard_response.status_code == 200
    body = scorecard_response.json()
    assert body["symbols_with_snapshots"] >= 5
    assert body["actionable_signals"] >= 1
    assert any(item["symbol"] == "NVDA" for item in body["items"])
    assert any(item["outcome"] == "target_hit" for item in body["items"])
    assert any(stat["target_hits"] >= 1 for stat in body["setup_stats"])
