from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from zoneinfo import ZoneInfo

from app.models import CandleHistoryResponse, CandleRecord, IntradayFeatureSnapshot, MarketClock, QuoteSnapshot


US_EASTERN = ZoneInfo("America/New_York")


def _to_eastern(candle: CandleRecord) -> CandleRecord:
    return candle


def _is_regular_session_bar(bar: CandleRecord) -> bool:
    local_timestamp = bar.timestamp.astimezone(US_EASTERN)
    return time(hour=9, minute=30) <= local_timestamp.time() <= time(hour=16, minute=0)


def regular_session_bars(candles: CandleHistoryResponse) -> list[CandleRecord]:
    return [item for item in candles.items if _is_regular_session_bar(item)]


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _return_pct(current: float, previous: float) -> float:
    if previous == 0:
        return 0.0
    return ((current / previous) - 1) * 100


def _sma(values: list[float], length: int) -> float:
    if not values:
        return 0.0
    if len(values) < length:
        return _mean(values)
    return _mean(values[-length:])


def _vwap(bars: list[CandleRecord]) -> float | None:
    if not bars:
        return None

    cumulative_pv = 0.0
    cumulative_volume = 0
    for bar in bars:
        typical_price = (bar.high + bar.low + bar.close) / 3
        cumulative_pv += typical_price * bar.volume
        cumulative_volume += bar.volume

    if cumulative_volume == 0:
        return None
    return cumulative_pv / cumulative_volume


def _opening_range(bars: list[CandleRecord]) -> tuple[float | None, float | None]:
    if len(bars) < 3:
        return (None, None)
    opening_bars = bars[:3]
    return (
        max(bar.high for bar in opening_bars),
        min(bar.low for bar in opening_bars)
    )


def _relative_volume(bars: list[CandleRecord]) -> float:
    if len(bars) < 6:
        return 1.0
    recent = bars[-3:]
    baseline = bars[:-3][-12:] or bars[:-3]
    baseline_average = _mean([bar.volume for bar in baseline]) or 1.0
    recent_average = _mean([bar.volume for bar in recent])
    return recent_average / baseline_average


def _momentum_pct(bars: list[CandleRecord], lookback_bars: int) -> float:
    if len(bars) <= lookback_bars:
        return 0.0
    return _return_pct(bars[-1].close, bars[-1 - lookback_bars].close)


def _trend_alignment(
    execution_bars: list[CandleRecord],
    confirmation_bars: list[CandleRecord],
    current_price: float,
    vwap: float | None
) -> str:
    execution_closes = [bar.close for bar in execution_bars]
    confirmation_closes = [bar.close for bar in confirmation_bars]
    execution_trend = _sma(execution_closes, 8)
    confirmation_trend = _sma(confirmation_closes, 4)

    bullish = current_price >= execution_trend and current_price >= confirmation_trend
    bearish = current_price <= execution_trend and current_price <= confirmation_trend
    if vwap is not None:
        bullish = bullish and current_price >= vwap
        bearish = bearish and current_price <= vwap

    if bullish:
        return "bullish"
    if bearish:
        return "bearish"
    return "mixed"


def _breakout_state(
    current_price: float,
    session_high: float | None,
    session_low: float | None,
    opening_range_high: float | None,
    opening_range_low: float | None
) -> str:
    if opening_range_high is not None and current_price >= opening_range_high:
        return "above_range"
    if opening_range_low is not None and current_price <= opening_range_low:
        return "below_range"
    if (
        session_high is not None
        and opening_range_high is not None
        and session_high > opening_range_high
        and current_price < opening_range_high
    ):
        return "failed_breakout"
    if (
        session_low is not None
        and opening_range_low is not None
        and session_low < opening_range_low
        and current_price > opening_range_low
    ):
        return "failed_breakdown"
    return "inside_range"


@dataclass(frozen=True)
class IntradayFeatureBundle:
    snapshot: IntradayFeatureSnapshot
    execution_bars: list[CandleRecord]
    confirmation_bars: list[CandleRecord]


def build_intraday_features(
    *,
    quote: QuoteSnapshot,
    execution_candles: CandleHistoryResponse,
    confirmation_candles: CandleHistoryResponse,
    market_clock: MarketClock
) -> IntradayFeatureBundle:
    execution_bars = regular_session_bars(execution_candles) or execution_candles.items
    confirmation_bars = regular_session_bars(confirmation_candles) or confirmation_candles.items
    opening_range_high, opening_range_low = _opening_range(execution_bars)
    session_high = max((bar.high for bar in execution_bars), default=None)
    session_low = min((bar.low for bar in execution_bars), default=None)
    vwap = _vwap(execution_bars)
    momentum_5m_pct = _momentum_pct(execution_bars, 3)
    momentum_15m_pct = _momentum_pct(confirmation_bars, 2)
    trend_alignment = _trend_alignment(
        execution_bars,
        confirmation_bars,
        quote.last,
        vwap
    )

    if trend_alignment == "bullish" and session_high:
        pullback_depth_pct = max(0.0, ((session_high - quote.last) / session_high) * 100)
    elif trend_alignment == "bearish" and session_low:
        pullback_depth_pct = max(0.0, ((quote.last - session_low) / quote.last) * 100)
    else:
        midpoint = (
            ((opening_range_high or quote.last) + (opening_range_low or quote.last)) / 2
            if opening_range_high is not None and opening_range_low is not None
            else quote.last
        )
        pullback_depth_pct = abs(_return_pct(quote.last, midpoint))

    session_range_pct = (
        _return_pct(session_high, session_low)
        if session_high is not None and session_low is not None and session_low > 0
        else 0.0
    )

    snapshot = IntradayFeatureSnapshot(
        execution_interval="5min",
        confirmation_interval="15min",
        session_phase=market_clock.phase,
        opening_range_high=opening_range_high,
        opening_range_low=opening_range_low,
        session_high=session_high,
        session_low=session_low,
        vwap=vwap,
        momentum_5m_pct=round(momentum_5m_pct, 4),
        momentum_15m_pct=round(momentum_15m_pct, 4),
        pullback_depth_pct=round(pullback_depth_pct, 4),
        relative_volume=round(_relative_volume(execution_bars), 4),
        session_range_pct=round(session_range_pct, 4),
        trend_alignment=trend_alignment,  # type: ignore[arg-type]
        breakout_state=_breakout_state(
            quote.last,
            session_high,
            session_low,
            opening_range_high,
            opening_range_low
        ),  # type: ignore[arg-type]
        distance_to_stop_pct=None
    )

    return IntradayFeatureBundle(
        snapshot=snapshot,
        execution_bars=execution_bars,
        confirmation_bars=confirmation_bars
    )
