from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timezone
from typing import Protocol
from zoneinfo import ZoneInfo

from app.db import DatabaseSession
from app.models import (
    MarketClock,
    MarketOverviewResponse,
    PaperPortfolioSummary,
    PaperPositionRecord,
    QuoteSnapshot,
    RiskMetric,
    RiskSnapshot,
    SessionResponse,
    SignalAction,
    SignalAlert,
    SignalEntryState,
    SignalFocus,
    SignalPortfolioState,
    SignalRule,
    SignalSetupType,
    SignalTrailingStop,
    SignalsResponse,
    TradingSignalRecord,
    WatchlistItemRecord
)
from app.repositories.paper_trading import PaperTradingRepository
from app.services.intraday_features import IntradayFeatureBundle, build_intraday_features
from app.services.market import (
    get_intraday_candle_history,
    get_market_clock,
    get_market_overview,
    get_quote_snapshot,
    get_risk_snapshot
)
from app.services.paper_trading import get_portfolio_summary, list_open_positions
from app.services.session import AuthenticatedSessionContext
from app.services.signal_tracking import list_signal_alerts, persist_signal_run
from app.services.watchlist import list_watchlist


US_EASTERN = ZoneInfo("America/New_York")
MODEL_CAPITAL_BASE = 100_000.0
MAX_TOTAL_EXPOSURE_PCT = 40.0
MAX_RISK_PER_TRADE_PCT = 0.4
MAX_SIGNAL_POSITION_SIZE_PCT = 12.0
MAX_DAILY_LOSS_PCT = 1.5
MAX_OPEN_POSITIONS = 4
MAX_SYMBOL_CONCENTRATION_PCT = 18.0
EOD_FLATTEN_MINUTES = 20
SIGNAL_SOURCE = "intraday-rule-engine"
DEFAULT_SIGNAL_UNIVERSE = ("NVDA", "AAPL", "SPY", "QQQ", "IWM")
SELL_SIGNAL_WARNING = "SELL is advisory only for fresh entries; the current paper flow still does not open short positions automatically."

SETUP_LABELS: dict[SignalSetupType, str] = {
    "opening_range_breakout": "Opening range breakout",
    "vwap_reclaim": "VWAP reclaim / breakdown",
    "pullback_continuation": "Pullback continuation",
    "failed_breakout": "Failed breakout / rejection",
    "no_trade": "Stand aside"
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _price(value: float | None) -> str:
    return f"${value:,.2f}" if value is not None else "n/a"


def _percent(value: float) -> str:
    return f"{value:.2f}%"


def _risk_utilization(metrics: list[RiskMetric]) -> float:
    utilizations = [
        (metric.current / metric.limit)
        for metric in metrics
        if metric.limit
    ]
    return max(utilizations, default=0.0)


def _eastern_day_start_iso() -> str:
    now_et = _now().astimezone(US_EASTERN)
    start_et = datetime.combine(now_et.date(), time.min, tzinfo=US_EASTERN)
    return start_et.astimezone(timezone.utc).isoformat()


def _stop_distance_pct(entry_price: float, stop_loss: float | None) -> float | None:
    if stop_loss is None or entry_price <= 0 or stop_loss <= 0:
        return None
    return abs(((entry_price - stop_loss) / entry_price) * 100)


def _entry_zone(trigger_price: float | None) -> str | None:
    if trigger_price is None:
        return None
    lower = round(trigger_price * 0.999, 2)
    upper = round(trigger_price * 1.0015, 2)
    return f"{_price(lower)} - {_price(upper)}"


def _long_targets(entry_price: float, stop_loss: float) -> tuple[float, float, float]:
    risk_per_share = max(0.01, entry_price - stop_loss)
    take_profit1 = round(entry_price + (risk_per_share * 1.5), 2)
    take_profit2 = round(entry_price + (risk_per_share * 2.25), 2)
    risk_reward = round((take_profit1 - entry_price) / risk_per_share, 2)
    return (take_profit1, take_profit2, risk_reward)


def _short_targets(entry_price: float, stop_loss: float) -> tuple[float, float, float]:
    risk_per_share = max(0.01, stop_loss - entry_price)
    take_profit1 = round(entry_price - (risk_per_share * 1.5), 2)
    take_profit2 = round(entry_price - (risk_per_share * 2.25), 2)
    risk_reward = round((entry_price - take_profit1) / risk_per_share, 2)
    return (take_profit1, take_profit2, risk_reward)


def _portfolio_state(
    summary: PaperPortfolioSummary | None,
    risk: RiskSnapshot,
    market_clock: MarketClock,
    daily_realized_pnl: float
) -> SignalPortfolioState:
    gross_exposure = round(summary.gross_exposure if summary else 0.0, 2)
    open_positions = summary.positions if summary else 0
    gross_exposure_pct = round(
        _clamp((gross_exposure / MODEL_CAPITAL_BASE) * 100, 0.0, 100.0),
        2
    )
    available_exposure_pct = round(
        max(0.0, MAX_TOTAL_EXPOSURE_PCT - gross_exposure_pct),
        2
    )
    risk_utilization_pct = round(_risk_utilization(risk.metrics) * 100, 1)
    current_unrealized = summary.unrealized_pnl if summary else 0.0
    daily_pnl = round(daily_realized_pnl + current_unrealized, 2)
    daily_pnl_pct = round((daily_pnl / MODEL_CAPITAL_BASE) * 100, 3)
    daily_loss_limit_hit = daily_pnl_pct <= -MAX_DAILY_LOSS_PCT
    flatten_before_close = (
        market_clock.minutes_to_close is not None
        and market_clock.minutes_to_close <= EOD_FLATTEN_MINUTES
    )

    warnings: list[str] = []
    if gross_exposure_pct >= MAX_TOTAL_EXPOSURE_PCT:
        warnings.append("Gross exposure is already at the intraday cap, so fresh trades stay blocked.")
    elif gross_exposure_pct >= MAX_TOTAL_EXPOSURE_PCT - 6:
        warnings.append("Gross exposure is close to the intraday cap, so new size should stay smaller than normal.")
    if open_positions >= MAX_OPEN_POSITIONS:
        warnings.append("Max open intraday positions is already reached.")
    if daily_loss_limit_hit:
        warnings.append("The max daily loss gate is already hit, so no fresh entries should be taken.")
    if flatten_before_close:
        warnings.append("The session is close to the bell, so fresh entries should stand down and open trades should prepare to flatten.")
    if risk_utilization_pct >= 90:
        warnings.append("At least one portfolio risk meter is effectively at its limit.")

    return SignalPortfolioState(
        capital_base=MODEL_CAPITAL_BASE,
        gross_exposure=gross_exposure,
        gross_exposure_pct=gross_exposure_pct,
        available_exposure_pct=available_exposure_pct,
        max_total_exposure_pct=MAX_TOTAL_EXPOSURE_PCT,
        max_risk_per_trade_pct=MAX_RISK_PER_TRADE_PCT,
        max_daily_loss_pct=MAX_DAILY_LOSS_PCT,
        max_open_positions=MAX_OPEN_POSITIONS,
        max_symbol_concentration_pct=MAX_SYMBOL_CONCENTRATION_PCT,
        open_positions=open_positions,
        risk_utilization_pct=risk_utilization_pct,
        daily_pnl=daily_pnl,
        daily_pnl_pct=daily_pnl_pct,
        daily_loss_limit_hit=daily_loss_limit_hit,
        flatten_before_close=flatten_before_close,
        warnings=warnings
    )


def _symbol_concentration_pct(position: PaperPositionRecord | None) -> float:
    if position is None:
        return 0.0
    return round((position.market_value / MODEL_CAPITAL_BASE) * 100, 2)


def _recommended_size_pct(
    entry_price: float,
    stop_loss: float,
    portfolio: SignalPortfolioState,
    position: PaperPositionRecord | None
) -> float:
    if position is not None:
        return round(_symbol_concentration_pct(position), 2)

    stop_distance_pct = _stop_distance_pct(entry_price, stop_loss)
    if stop_distance_pct is None or stop_distance_pct <= 0:
        return 0.0

    size_pct_from_risk = (MAX_RISK_PER_TRADE_PCT * 100) / stop_distance_pct
    return round(
        min(
            MAX_SIGNAL_POSITION_SIZE_PCT,
            portfolio.available_exposure_pct,
            MAX_SYMBOL_CONCENTRATION_PCT,
            size_pct_from_risk
        ),
        2
    )


@dataclass(frozen=True)
class SignalContext:
    symbol: str
    quote: QuoteSnapshot
    features: IntradayFeatureBundle
    watchlist_item: WatchlistItemRecord | None
    position: PaperPositionRecord | None
    market_overview: MarketOverviewResponse
    market_clock: MarketClock
    risk_snapshot: RiskSnapshot
    portfolio: SignalPortfolioState


@dataclass(frozen=True)
class SetupCandidate:
    setup_type: SignalSetupType
    action: SignalAction
    entry_state: SignalEntryState
    strategy_type: str
    timeframe: str
    is_actionable: bool
    score: int
    trigger_price: float | None
    entry_price: float | None
    stop_loss: float | None
    take_profit1: float | None
    take_profit2: float | None
    risk_reward: float | None
    thesis: str
    invalidation: str
    next_watch: str
    reasons: list[str]
    warnings: list[str]
    entry_rules: list[SignalRule]
    exit_rules: list[SignalRule]
    trailing_stop: SignalTrailingStop | None = None


class SignalEngine(Protocol):
    def evaluate(self, context: SignalContext) -> TradingSignalRecord:
        ...


def _stand_aside_candidate(
    context: SignalContext,
    *,
    reasons: list[str],
    warnings: list[str],
    next_watch: str,
    timeframe: str = "5m execution / 15m confirmation"
) -> SetupCandidate:
    entry_rules = [
        SignalRule(
            label="Session window",
            status="blocked" if context.market_clock.phase in {"premarket", "near_close", "after_hours", "closed"} else "watch",
            detail=f"Current phase is {context.market_clock.phase.replace('_', ' ')}."
        ),
        SignalRule(
            label="Trend alignment",
            status="watch",
            detail=f"Trend alignment is {context.features.snapshot.trend_alignment} and no clean intraday setup is active."
        ),
        SignalRule(
            label="Risk budget",
            status="blocked" if context.portfolio.daily_loss_limit_hit else "watch",
            detail=(
                "Daily loss gate is active."
                if context.portfolio.daily_loss_limit_hit
                else f"Available exposure is {_percent(context.portfolio.available_exposure_pct)}."
            )
        )
    ]
    exit_rules = [
        SignalRule(label="Protective stop", status="watch", detail="No active trade means no stop needs to be carried."),
        SignalRule(label="End-of-day flatten", status="watch", detail="Stay flat into the close unless a cleaner setup forms earlier."),
        SignalRule(label="Setup activation", status="watch", detail=next_watch)
    ]
    return SetupCandidate(
        setup_type="no_trade",
        action="NO_TRADE",
        entry_state="stand_aside",
        strategy_type=SETUP_LABELS["no_trade"],
        timeframe=timeframe,
        is_actionable=False,
        score=28,
        trigger_price=None,
        entry_price=None,
        stop_loss=None,
        take_profit1=None,
        take_profit2=None,
        risk_reward=None,
        thesis=f"Stand aside in {context.symbol} because there is no clean intraday trade right now.",
        invalidation=f"Do nothing unless {context.symbol} starts trading through a cleaner intraday trigger.",
        next_watch=next_watch,
        reasons=reasons,
        warnings=warnings,
        entry_rules=entry_rules,
        exit_rules=exit_rules,
        trailing_stop=None
    )


def _risk_blocked(context: SignalContext, entry_price: float, stop_loss: float) -> bool:
    size_pct = _recommended_size_pct(entry_price, stop_loss, context.portfolio, context.position)
    concentration_pct = _symbol_concentration_pct(context.position)
    return any(
        (
            context.portfolio.daily_loss_limit_hit,
            context.portfolio.open_positions >= MAX_OPEN_POSITIONS,
            context.portfolio.available_exposure_pct < 2.0,
            context.portfolio.flatten_before_close,
            concentration_pct >= MAX_SYMBOL_CONCENTRATION_PCT,
            size_pct <= 0
        )
    )


def _build_signal_record(context: SignalContext, candidate: SetupCandidate) -> TradingSignalRecord:
    stop_distance_pct = _stop_distance_pct(
        candidate.entry_price or context.quote.last,
        candidate.stop_loss
    )
    features = context.features.snapshot.model_copy(
        update={"distance_to_stop_pct": round(stop_distance_pct, 4) if stop_distance_pct is not None else None}
    )
    confidence = int(
        round(
            _clamp(
                candidate.score + (8 if candidate.is_actionable else -4) - (4 if len(candidate.warnings) >= 3 else 0),
                10,
                99
            )
        )
    )
    recommended_size = (
        _recommended_size_pct(
            candidate.entry_price or context.quote.last,
            candidate.stop_loss or context.quote.last,
            context.portfolio,
            context.position
        )
        if candidate.entry_price is not None and candidate.stop_loss is not None
        else (_symbol_concentration_pct(context.position) if context.position else 0.0)
    )

    return TradingSignalRecord(
        symbol=context.symbol,
        action=candidate.action,
        confidence=confidence,
        score=candidate.score,
        setup_type=candidate.setup_type,
        entry_state=candidate.entry_state,
        strategy_type=candidate.strategy_type,
        timeframe=candidate.timeframe,
        thesis=candidate.thesis,
        trigger_price=candidate.trigger_price,
        entry_price=candidate.entry_price,
        entry_zone=_entry_zone(candidate.trigger_price),
        stop_loss=candidate.stop_loss,
        take_profit1=candidate.take_profit1,
        take_profit2=candidate.take_profit2,
        invalidation=candidate.invalidation,
        risk_reward=candidate.risk_reward,
        position_size_pct=recommended_size,
        reasons=candidate.reasons[:4],
        warnings=candidate.warnings[:4],
        timestamp=_now(),
        is_actionable=candidate.is_actionable,
        has_position=context.position is not None,
        market_data_source=context.quote.source,
        market_data_quality=context.quote.quality,
        current_position=context.position,
        opportunity_id=None,
        next_watch=candidate.next_watch,
        entry_rules=candidate.entry_rules,
        exit_rules=candidate.exit_rules,
        trailing_stop=candidate.trailing_stop,
        intraday_features=features
    )


class RuleBasedIntradaySignalEngine:
    def evaluate(self, context: SignalContext) -> TradingSignalRecord:
        if context.position is not None:
            return _build_signal_record(context, self._manage_position(context))

        if context.market_clock.phase in {"premarket", "after_hours", "closed"}:
            return _build_signal_record(
                context,
                _stand_aside_candidate(
                    context,
                    reasons=[
                        f"{context.symbol} is outside the core day-trading window because the market phase is {context.market_clock.phase.replace('_', ' ')}.",
                        "Opening range and VWAP signals are lower quality before the regular session has formed."
                    ],
                    warnings=[
                        "Premarket and after-hours price action can move on thin liquidity and wider spreads."
                    ],
                    next_watch=f"Wait for the regular session to open and for the first 15 minutes of price discovery to complete in {context.symbol}."
                )
            )

        candidates = [
            self._opening_range_breakout(context),
            self._vwap_reclaim(context),
            self._pullback_continuation(context),
            self._failed_breakout(context)
        ]
        actionable = [candidate for candidate in candidates if candidate.is_actionable]
        if actionable:
            return _build_signal_record(context, max(actionable, key=lambda candidate: candidate.score))

        waiting = [
            candidate
            for candidate in candidates
            if candidate.entry_state == "wait_for_confirmation"
        ]
        if waiting:
            return _build_signal_record(context, max(waiting, key=lambda candidate: candidate.score))

        return _build_signal_record(context, self._no_trade(context))

    def _opening_range_breakout(self, context: SignalContext) -> SetupCandidate:
        features = context.features.snapshot
        or_high = features.opening_range_high
        or_low = features.opening_range_low
        vwap = features.vwap
        current_price = context.quote.last
        bullish = (
            or_high is not None
            and current_price >= or_high * 1.001
            and features.trend_alignment == "bullish"
            and (vwap is None or current_price >= vwap)
            and features.relative_volume >= 1.05
            and features.momentum_5m_pct >= 0.18
        )
        bearish = (
            or_low is not None
            and current_price <= or_low * 0.999
            and features.trend_alignment == "bearish"
            and (vwap is None or current_price <= vwap)
            and features.relative_volume >= 1.05
            and features.momentum_5m_pct <= -0.18
        )
        wait_for_long = (
            or_high is not None
            and features.trend_alignment == "bullish"
            and current_price < or_high
            and ((or_high - current_price) / or_high) * 100 <= 0.35
        )
        wait_for_short = (
            or_low is not None
            and features.trend_alignment == "bearish"
            and current_price > or_low
            and ((current_price - or_low) / current_price) * 100 <= 0.35
        )

        if bullish and or_low is not None:
            entry_price = current_price
            stop_loss = round(max(or_low, (vwap or or_low)), 2)
            if stop_loss >= entry_price:
                stop_loss = round(entry_price * 0.994, 2)
            take_profit1, take_profit2, risk_reward = _long_targets(entry_price, stop_loss)
            risk_blocked = _risk_blocked(context, entry_price, stop_loss)
            return SetupCandidate(
                setup_type="opening_range_breakout",
                action="BUY" if not risk_blocked else "NO_TRADE",
                entry_state="enter_now" if not risk_blocked else "stand_aside",
                strategy_type=SETUP_LABELS["opening_range_breakout"],
                timeframe="5m execution / 15m confirmation",
                is_actionable=not risk_blocked,
                score=82,
                trigger_price=round(or_high * 1.001, 2),
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit1=take_profit1,
                take_profit2=take_profit2,
                risk_reward=risk_reward,
                thesis=(
                    f"Buy {context.symbol} now because the opening range breakout is already confirmed on intraday breadth, momentum, and volume."
                    if not risk_blocked
                    else f"Opening range breakout is active in {context.symbol}, but portfolio risk gates block a fresh entry."
                ),
                invalidation=f"Invalidate the breakout if {context.symbol} falls back through {_price(stop_loss)} or loses the opening range.",
                next_watch=f"Stay with the breakout only while {context.symbol} holds above {_price(or_high)} and keeps accepting above VWAP.",
                reasons=[
                    f"Price is through the opening range high at {_price(or_high)}.",
                    f"Intraday momentum is {_percent(features.momentum_5m_pct)} on 5-minute bars with relative volume at {features.relative_volume:.2f}x.",
                    f"Trend alignment is {features.trend_alignment} and price is {'above' if vwap and current_price >= vwap else 'not below'} VWAP."
                ],
                warnings=context.portfolio.warnings + ([] if not risk_blocked else ["Risk gates are blocking fresh day-trade entries right now."]),
                entry_rules=[
                    SignalRule(label="Opening range break", status="met", detail=f"Price is already above {_price(or_high)}."),
                    SignalRule(label="Volume confirmation", status="met", detail=f"Relative volume is {features.relative_volume:.2f}x."),
                    SignalRule(label="Risk budget", status="blocked" if risk_blocked else "met", detail=f"Available exposure is {_percent(context.portfolio.available_exposure_pct)}.")
                ],
                exit_rules=[
                    SignalRule(label="Protective stop", status="watch", detail=f"Exit if price loses {_price(stop_loss)}."),
                    SignalRule(label="Target 1", status="watch", detail=f"Scale at {_price(take_profit1)}."),
                    SignalRule(label="End-of-day flatten", status="watch", detail="Flatten before the session closes even if the setup still looks fine.")
                ],
                trailing_stop=SignalTrailingStop(
                    enabled=False,
                    activation_price=round(take_profit1, 2),
                    trail_percent=0.6,
                    detail="Once the first target clears, trail under fresh 5-minute higher lows instead of widening risk."
                )
            )

        if bearish and or_high is not None:
            entry_price = current_price
            stop_loss = round(min(or_high, (vwap or or_high)) if (vwap or or_high) > entry_price else or_high, 2)
            if stop_loss <= entry_price:
                stop_loss = round(entry_price * 1.006, 2)
            take_profit1, take_profit2, risk_reward = _short_targets(entry_price, stop_loss)
            risk_blocked = _risk_blocked(context, entry_price, stop_loss)
            warnings = [SELL_SIGNAL_WARNING]
            if risk_blocked:
                warnings.append("Risk gates are blocking fresh day-trade entries right now.")
            return SetupCandidate(
                setup_type="opening_range_breakout",
                action="SELL" if not risk_blocked else "NO_TRADE",
                entry_state="enter_now" if not risk_blocked else "stand_aside",
                strategy_type=SETUP_LABELS["opening_range_breakout"],
                timeframe="5m execution / 15m confirmation",
                is_actionable=not risk_blocked,
                score=79,
                trigger_price=round(or_low * 0.999, 2),
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit1=take_profit1,
                take_profit2=take_profit2,
                risk_reward=risk_reward,
                thesis=(
                    f"Sell {context.symbol} now because the opening range has broken down and the tape is not accepting back above intraday support."
                    if not risk_blocked
                    else f"Opening range breakdown is active in {context.symbol}, but portfolio risk gates block a fresh short-side decision."
                ),
                invalidation=f"Invalidate the breakdown if {context.symbol} reclaims {_price(stop_loss)} and holds above it.",
                next_watch=f"Stay with the breakdown only while {context.symbol} remains below {_price(or_low)} and below VWAP.",
                reasons=[
                    f"Price is through the opening range low at {_price(or_low)}.",
                    f"Intraday momentum is {_percent(features.momentum_5m_pct)} with trend alignment marked {features.trend_alignment}.",
                    f"Relative volume is {features.relative_volume:.2f}x, which is enough to respect the breakdown."
                ],
                warnings=context.portfolio.warnings + warnings,
                entry_rules=[
                    SignalRule(label="Opening range break", status="met", detail=f"Price is already below {_price(or_low)}."),
                    SignalRule(label="Volume confirmation", status="met", detail=f"Relative volume is {features.relative_volume:.2f}x."),
                    SignalRule(label="Risk budget", status="blocked" if risk_blocked else "met", detail=f"Available exposure is {_percent(context.portfolio.available_exposure_pct)}.")
                ],
                exit_rules=[
                    SignalRule(label="Protective stop", status="watch", detail=f"Exit if price reclaims {_price(stop_loss)}."),
                    SignalRule(label="Target 1", status="watch", detail=f"Take partials near {_price(take_profit1)}."),
                    SignalRule(label="End-of-day flatten", status="watch", detail="Flatten before the session closes even on a working short bias.")
                ]
            )

        if wait_for_long and or_high is not None:
            return SetupCandidate(
                setup_type="opening_range_breakout",
                action="NO_TRADE",
                entry_state="wait_for_confirmation",
                strategy_type=SETUP_LABELS["opening_range_breakout"],
                timeframe="5m execution / 15m confirmation",
                is_actionable=False,
                score=58,
                trigger_price=round(or_high * 1.001, 2),
                entry_price=round(or_high * 1.001, 2),
                stop_loss=round((or_low or or_high * 0.994), 2),
                take_profit1=None,
                take_profit2=None,
                risk_reward=None,
                thesis=f"Wait on {context.symbol}; the opening range breakout setup is forming but price has not confirmed through the trigger yet.",
                invalidation=f"Stand aside if {context.symbol} loses the opening range low before breaking {_price(or_high)}.",
                next_watch=f"Buy only after a clean push through {_price(or_high)} with volume holding above the recent 5-minute average.",
                reasons=[
                    f"{context.symbol} is sitting just under the opening range high at {_price(or_high)}.",
                    f"Trend alignment is {features.trend_alignment} and relative volume is {features.relative_volume:.2f}x."
                ],
                warnings=["Do not front-run the breakout while price is still inside the range."],
                entry_rules=[
                    SignalRule(label="Opening range break", status="watch", detail=f"Trigger is {_price(or_high)}."),
                    SignalRule(label="Volume confirmation", status="watch", detail=f"Relative volume is {features.relative_volume:.2f}x."),
                    SignalRule(label="Risk budget", status="met", detail=f"Available exposure is {_percent(context.portfolio.available_exposure_pct)}.")
                ],
                exit_rules=[
                    SignalRule(label="Protective stop", status="watch", detail="No entry yet, so keep the setup on watch only."),
                    SignalRule(label="Target 1", status="watch", detail="Targets become active only after the breakout confirms."),
                    SignalRule(label="End-of-day flatten", status="watch", detail="Ignore the setup if the trigger only arrives too close to the close.")
                ]
            )

        if wait_for_short and or_low is not None:
            return SetupCandidate(
                setup_type="opening_range_breakout",
                action="NO_TRADE",
                entry_state="wait_for_confirmation",
                strategy_type=SETUP_LABELS["opening_range_breakout"],
                timeframe="5m execution / 15m confirmation",
                is_actionable=False,
                score=56,
                trigger_price=round(or_low * 0.999, 2),
                entry_price=round(or_low * 0.999, 2),
                stop_loss=round((or_high or or_low * 1.006), 2),
                take_profit1=None,
                take_profit2=None,
                risk_reward=None,
                thesis=f"Wait on {context.symbol}; the opening range breakdown is close, but the trigger has not printed yet.",
                invalidation=f"Stand aside if {context.symbol} reclaims the upper half of the opening range before breaking down.",
                next_watch=f"Sell only after a clean loss of {_price(or_low)} with volume staying heavy.",
                reasons=[
                    f"{context.symbol} is hovering near the opening range low at {_price(or_low)}.",
                    f"Trend alignment is {features.trend_alignment} and momentum is {_percent(features.momentum_5m_pct)}."
                ],
                warnings=["SELL is still advisory only for fresh entries while paper shorting is not wired."],
                entry_rules=[
                    SignalRule(label="Opening range break", status="watch", detail=f"Trigger is {_price(or_low)}."),
                    SignalRule(label="Volume confirmation", status="watch", detail=f"Relative volume is {features.relative_volume:.2f}x."),
                    SignalRule(label="Risk budget", status="met", detail=f"Available exposure is {_percent(context.portfolio.available_exposure_pct)}.")
                ],
                exit_rules=[
                    SignalRule(label="Protective stop", status="watch", detail="No entry yet, so the setup stays on watch only."),
                    SignalRule(label="Target 1", status="watch", detail="Targets become active only after the breakdown confirms."),
                    SignalRule(label="End-of-day flatten", status="watch", detail="Ignore the setup if the trigger only arrives too close to the close.")
                ]
            )

        return self._no_trade(context)

    def _vwap_reclaim(self, context: SignalContext) -> SetupCandidate:
        features = context.features.snapshot
        vwap = features.vwap
        current_price = context.quote.last
        if vwap is None:
            return self._no_trade(context)

        execution_bars = context.features.execution_bars
        recent_lows = [bar.low for bar in execution_bars[-3:]] if execution_bars else [current_price]
        prior_closes = [bar.close for bar in execution_bars[-6:]] if execution_bars else [current_price]
        long_reclaim = (
            current_price >= vwap * 1.001
            and min(prior_closes) < vwap
            and features.momentum_5m_pct >= 0.08
            and features.trend_alignment != "bearish"
        )
        short_breakdown = (
            current_price <= vwap * 0.999
            and max(prior_closes) > vwap
            and features.momentum_5m_pct <= -0.08
            and features.trend_alignment != "bullish"
        )
        waiting = abs(((current_price - vwap) / vwap) * 100) <= 0.12

        if long_reclaim:
            entry_price = current_price
            stop_loss = round(min(min(recent_lows), vwap * 0.9975), 2)
            take_profit1, take_profit2, risk_reward = _long_targets(entry_price, stop_loss)
            risk_blocked = _risk_blocked(context, entry_price, stop_loss)
            return SetupCandidate(
                setup_type="vwap_reclaim",
                action="BUY" if not risk_blocked else "NO_TRADE",
                entry_state="enter_now" if not risk_blocked else "stand_aside",
                strategy_type=SETUP_LABELS["vwap_reclaim"],
                timeframe="1m trigger / 5m structure / 15m confirmation",
                is_actionable=not risk_blocked,
                score=76,
                trigger_price=round(vwap * 1.001, 2),
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit1=take_profit1,
                take_profit2=take_profit2,
                risk_reward=risk_reward,
                thesis=(
                    f"Buy {context.symbol} now because price has reclaimed VWAP with enough intraday momentum to treat it as a live long setup."
                    if not risk_blocked
                    else f"{context.symbol} has reclaimed VWAP, but current risk gates block a fresh entry."
                ),
                invalidation=f"Invalidate the reclaim if {context.symbol} loses VWAP and the recent 5-minute swing low at {_price(stop_loss)}.",
                next_watch=f"Hold the setup only while {context.symbol} keeps accepting above VWAP near {_price(vwap)}.",
                reasons=[
                    f"Price is back above VWAP at {_price(vwap)} after spending time below it earlier.",
                    f"5-minute momentum has turned positive at {_percent(features.momentum_5m_pct)}.",
                    f"Relative volume is {features.relative_volume:.2f}x, which is enough to respect the reclaim."
                ],
                warnings=context.portfolio.warnings + ([] if not risk_blocked else ["Risk gates are blocking fresh day-trade entries right now."]),
                entry_rules=[
                    SignalRule(label="VWAP reclaim", status="met", detail=f"Price is above {_price(vwap)}."),
                    SignalRule(label="Momentum turn", status="met", detail=f"5-minute momentum is {_percent(features.momentum_5m_pct)}."),
                    SignalRule(label="Risk budget", status="blocked" if risk_blocked else "met", detail=f"Available exposure is {_percent(context.portfolio.available_exposure_pct)}.")
                ],
                exit_rules=[
                    SignalRule(label="VWAP failure", status="watch", detail=f"Exit if price loses {_price(vwap)} and breaks {_price(stop_loss)}."),
                    SignalRule(label="Target 1", status="watch", detail=f"Trim near {_price(take_profit1)}."),
                    SignalRule(label="End-of-day flatten", status="watch", detail="Flatten before the bell even if the reclaim stays intact.")
                ]
            )

        if short_breakdown:
            entry_price = current_price
            stop_loss = round(max(max(bar.high for bar in execution_bars[-3:]), vwap * 1.0025), 2)
            take_profit1, take_profit2, risk_reward = _short_targets(entry_price, stop_loss)
            risk_blocked = _risk_blocked(context, entry_price, stop_loss)
            warnings = [SELL_SIGNAL_WARNING]
            if risk_blocked:
                warnings.append("Risk gates are blocking fresh day-trade entries right now.")
            return SetupCandidate(
                setup_type="vwap_reclaim",
                action="SELL" if not risk_blocked else "NO_TRADE",
                entry_state="enter_now" if not risk_blocked else "stand_aside",
                strategy_type=SETUP_LABELS["vwap_reclaim"],
                timeframe="1m trigger / 5m structure / 15m confirmation",
                is_actionable=not risk_blocked,
                score=74,
                trigger_price=round(vwap * 0.999, 2),
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit1=take_profit1,
                take_profit2=take_profit2,
                risk_reward=risk_reward,
                thesis=(
                    f"Sell {context.symbol} now because price has broken back below VWAP and the intraday reclaim attempt has failed."
                    if not risk_blocked
                    else f"{context.symbol} has lost VWAP, but current risk gates block a fresh short-side decision."
                ),
                invalidation=f"Invalidate the breakdown if {context.symbol} reclaims VWAP and pushes back above {_price(stop_loss)}.",
                next_watch=f"Stay with the breakdown only while {context.symbol} remains below VWAP near {_price(vwap)}.",
                reasons=[
                    f"Price is back below VWAP at {_price(vwap)}.",
                    f"5-minute momentum is {_percent(features.momentum_5m_pct)} and trend alignment is {features.trend_alignment}.",
                    f"The last reclaim attempt failed, which turns VWAP into resistance instead of support."
                ],
                warnings=context.portfolio.warnings + warnings,
                entry_rules=[
                    SignalRule(label="VWAP loss", status="met", detail=f"Price is below {_price(vwap)}."),
                    SignalRule(label="Momentum turn", status="met", detail=f"5-minute momentum is {_percent(features.momentum_5m_pct)}."),
                    SignalRule(label="Risk budget", status="blocked" if risk_blocked else "met", detail=f"Available exposure is {_percent(context.portfolio.available_exposure_pct)}.")
                ],
                exit_rules=[
                    SignalRule(label="VWAP reclaim", status="watch", detail=f"Exit if price reclaims {_price(vwap)}."),
                    SignalRule(label="Target 1", status="watch", detail=f"Trim near {_price(take_profit1)}."),
                    SignalRule(label="End-of-day flatten", status="watch", detail="Flatten before the bell even if the breakdown keeps working.")
                ]
            )

        if waiting:
            return SetupCandidate(
                setup_type="vwap_reclaim",
                action="NO_TRADE",
                entry_state="wait_for_confirmation",
                strategy_type=SETUP_LABELS["vwap_reclaim"],
                timeframe="1m trigger / 5m structure / 15m confirmation",
                is_actionable=False,
                score=52,
                trigger_price=round(vwap, 2),
                entry_price=round(vwap, 2),
                stop_loss=None,
                take_profit1=None,
                take_profit2=None,
                risk_reward=None,
                thesis=f"Wait on {context.symbol}; price is sitting on VWAP and still needs a clean acceptance or rejection before it becomes tradable.",
                invalidation=f"Ignore the setup if {context.symbol} keeps chopping around VWAP without follow-through.",
                next_watch=f"Wait for {context.symbol} to either hold decisively above {_price(vwap)} or reject hard below it.",
                reasons=[
                    f"Price is still hovering around VWAP at {_price(vwap)}.",
                    f"That keeps the setup in wait mode instead of turning it into a trade now."
                ],
                warnings=["Do not force a VWAP trade while price is still chopping through the line."],
                entry_rules=[
                    SignalRule(label="VWAP decision", status="watch", detail=f"VWAP is {_price(vwap)}."),
                    SignalRule(label="Momentum turn", status="watch", detail=f"5-minute momentum is {_percent(features.momentum_5m_pct)}."),
                    SignalRule(label="Risk budget", status="met", detail=f"Available exposure is {_percent(context.portfolio.available_exposure_pct)}.")
                ],
                exit_rules=[
                    SignalRule(label="Protective stop", status="watch", detail="No entry yet, so keep the setup on watch only."),
                    SignalRule(label="Target 1", status="watch", detail="Targets become active only after VWAP acceptance or rejection confirms."),
                    SignalRule(label="End-of-day flatten", status="watch", detail="Ignore the setup if confirmation comes too late in the session.")
                ]
            )

        return self._no_trade(context)

    def _pullback_continuation(self, context: SignalContext) -> SetupCandidate:
        features = context.features.snapshot
        current_price = context.quote.last
        vwap = features.vwap or current_price
        recent_high = max((bar.high for bar in context.features.execution_bars[-3:]), default=current_price)
        recent_low = min((bar.low for bar in context.features.execution_bars[-3:]), default=current_price)
        tradable_pullback = (
            features.trend_alignment == "bullish"
            and features.pullback_depth_pct >= 0.15
            and features.pullback_depth_pct <= 1.25
            and current_price >= vwap
            and features.momentum_15m_pct > 0
            and current_price >= recent_high * 0.998
        )
        waiting = (
            features.trend_alignment == "bullish"
            and features.pullback_depth_pct >= 0.15
            and features.pullback_depth_pct <= 1.25
            and current_price < recent_high
        )

        if tradable_pullback:
            entry_price = current_price
            stop_loss = round(min(recent_low, vwap * 0.9975), 2)
            if stop_loss >= entry_price:
                stop_loss = round(entry_price * 0.995, 2)
            take_profit1, take_profit2, risk_reward = _long_targets(entry_price, stop_loss)
            risk_blocked = _risk_blocked(context, entry_price, stop_loss)
            return SetupCandidate(
                setup_type="pullback_continuation",
                action="BUY" if not risk_blocked else "NO_TRADE",
                entry_state="enter_now" if not risk_blocked else "stand_aside",
                strategy_type=SETUP_LABELS["pullback_continuation"],
                timeframe="5m pullback / 15m trend",
                is_actionable=not risk_blocked,
                score=72,
                trigger_price=round(recent_high, 2),
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit1=take_profit1,
                take_profit2=take_profit2,
                risk_reward=risk_reward,
                thesis=(
                    f"Buy {context.symbol} now because the intraday pullback has held trend support and is starting to continue back in the dominant direction."
                    if not risk_blocked
                    else f"{context.symbol} is setting up for a pullback continuation, but risk gates block the entry."
                ),
                invalidation=f"Invalidate the continuation if {context.symbol} loses {_price(stop_loss)} and falls back through the pullback low.",
                next_watch=f"Add only while {context.symbol} keeps holding above {_price(stop_loss)} and breaks the recent 5-minute pivot at {_price(recent_high)}.",
                reasons=[
                    f"Trend alignment is bullish across the short intraday windows.",
                    f"Pullback depth is {features.pullback_depth_pct:.2f}% and price is still holding above VWAP near {_price(vwap)}.",
                    f"15-minute momentum remains positive at {_percent(features.momentum_15m_pct)}."
                ],
                warnings=context.portfolio.warnings + ([] if not risk_blocked else ["Risk gates are blocking fresh day-trade entries right now."]),
                entry_rules=[
                    SignalRule(label="Trend alignment", status="met", detail="Short intraday windows are still aligned bullish."),
                    SignalRule(label="Healthy pullback", status="met", detail=f"Pullback depth is {features.pullback_depth_pct:.2f}%."),
                    SignalRule(label="Risk budget", status="blocked" if risk_blocked else "met", detail=f"Available exposure is {_percent(context.portfolio.available_exposure_pct)}.")
                ],
                exit_rules=[
                    SignalRule(label="Pullback low", status="watch", detail=f"Exit if price loses {_price(stop_loss)}."),
                    SignalRule(label="Target 1", status="watch", detail=f"Trim near {_price(take_profit1)}."),
                    SignalRule(label="End-of-day flatten", status="watch", detail="Flatten before the bell even if continuation remains orderly.")
                ]
            )

        if waiting:
            return SetupCandidate(
                setup_type="pullback_continuation",
                action="NO_TRADE",
                entry_state="wait_for_confirmation",
                strategy_type=SETUP_LABELS["pullback_continuation"],
                timeframe="5m pullback / 15m trend",
                is_actionable=False,
                score=50,
                trigger_price=round(recent_high, 2),
                entry_price=round(recent_high, 2),
                stop_loss=round(recent_low, 2),
                take_profit1=None,
                take_profit2=None,
                risk_reward=None,
                thesis=f"Wait on {context.symbol}; the pullback is still constructive, but price has not resumed through the trigger yet.",
                invalidation=f"Stand aside if {context.symbol} loses {_price(recent_low)} before retaking {_price(recent_high)}.",
                next_watch=f"Buy only after {context.symbol} trades back through the recent pivot at {_price(recent_high)}.",
                reasons=[
                    f"Trend alignment is bullish, but the pullback has not resolved back upward yet.",
                    f"That keeps the setup in wait mode instead of making it a trade now."
                ],
                warnings=["Wait for the pullback to re-accelerate before committing new size."],
                entry_rules=[
                    SignalRule(label="Trend alignment", status="met", detail="Short intraday windows are still aligned bullish."),
                    SignalRule(label="Continuation trigger", status="watch", detail=f"Trigger is {_price(recent_high)}."),
                    SignalRule(label="Risk budget", status="met", detail=f"Available exposure is {_percent(context.portfolio.available_exposure_pct)}.")
                ],
                exit_rules=[
                    SignalRule(label="Pullback failure", status="watch", detail=f"Stand aside if price loses {_price(recent_low)}."),
                    SignalRule(label="Target 1", status="watch", detail="Targets become active only after continuation confirms."),
                    SignalRule(label="End-of-day flatten", status="watch", detail="Ignore the setup if confirmation only comes too late in the session.")
                ]
            )

        return self._no_trade(context)

    def _failed_breakout(self, context: SignalContext) -> SetupCandidate:
        features = context.features.snapshot
        current_price = context.quote.last
        or_high = features.opening_range_high
        session_high = features.session_high or current_price
        vwap = features.vwap or current_price

        if features.breakout_state == "failed_breakout" and or_high is not None:
            entry_price = current_price
            stop_loss = round(max(session_high, vwap * 1.0025), 2)
            if stop_loss <= entry_price:
                stop_loss = round(entry_price * 1.006, 2)
            take_profit1, take_profit2, risk_reward = _short_targets(entry_price, stop_loss)
            risk_blocked = _risk_blocked(context, entry_price, stop_loss)
            warnings = [SELL_SIGNAL_WARNING]
            if risk_blocked:
                warnings.append("Risk gates are blocking fresh day-trade entries right now.")
            return SetupCandidate(
                setup_type="failed_breakout",
                action="SELL" if not risk_blocked else "NO_TRADE",
                entry_state="enter_now" if not risk_blocked else "stand_aside",
                strategy_type=SETUP_LABELS["failed_breakout"],
                timeframe="5m rejection / 15m confirmation",
                is_actionable=not risk_blocked,
                score=78,
                trigger_price=round(or_high, 2),
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit1=take_profit1,
                take_profit2=take_profit2,
                risk_reward=risk_reward,
                thesis=(
                    f"Sell {context.symbol} now because the breakout failed and price is back below the level that needed to hold."
                    if not risk_blocked
                    else f"{context.symbol} has a failed breakout setup, but risk gates block the short-side decision."
                ),
                invalidation=f"Invalidate the rejection if {context.symbol} reclaims {_price(stop_loss)} and holds above it.",
                next_watch=f"Stay short-biased only while {context.symbol} remains back under the failed breakout level at {_price(or_high)}.",
                reasons=[
                    f"Price traded above the breakout level but is now back below {_price(or_high)}.",
                    f"That turns the failed breakout into a rejection setup instead of a continuation.",
                    f"Trend alignment is {features.trend_alignment} with 5-minute momentum at {_percent(features.momentum_5m_pct)}."
                ],
                warnings=context.portfolio.warnings + warnings,
                entry_rules=[
                    SignalRule(label="Failed breakout", status="met", detail=f"Price is back below {_price(or_high)}."),
                    SignalRule(label="Momentum rollover", status="met", detail=f"5-minute momentum is {_percent(features.momentum_5m_pct)}."),
                    SignalRule(label="Risk budget", status="blocked" if risk_blocked else "met", detail=f"Available exposure is {_percent(context.portfolio.available_exposure_pct)}.")
                ],
                exit_rules=[
                    SignalRule(label="Reclaim stop", status="watch", detail=f"Exit if price reclaims {_price(stop_loss)}."),
                    SignalRule(label="Target 1", status="watch", detail=f"Trim near {_price(take_profit1)}."),
                    SignalRule(label="End-of-day flatten", status="watch", detail="Flatten before the bell even if the rejection keeps working.")
                ]
            )

        return self._no_trade(context)

    def _manage_position(self, context: SignalContext) -> SetupCandidate:
        assert context.position is not None

        position = context.position
        features = context.features.snapshot
        current_price = context.quote.last
        vwap = features.vwap or current_price
        or_low = features.opening_range_low or current_price * 0.995
        protective_stop = round(max(or_low, vwap * 0.9975) if current_price >= vwap else min(or_low, vwap), 2)
        if protective_stop >= current_price:
            protective_stop = round(current_price * 0.995, 2)

        take_profit1, take_profit2, risk_reward = _long_targets(position.average_cost, protective_stop)
        gain_pct = ((current_price - position.average_cost) / position.average_cost) * 100
        stop_hit = current_price <= protective_stop * 1.001
        target1_hit = current_price >= take_profit1

        if context.market_clock.phase in {"near_close", "after_hours", "closed"} or context.portfolio.flatten_before_close:
            return SetupCandidate(
                setup_type="no_trade",
                action="EXIT",
                entry_state="manage_position",
                strategy_type="End-of-day flatten",
                timeframe="Intraday risk management",
                is_actionable=True,
                score=88,
                trigger_price=None,
                entry_price=position.average_cost,
                stop_loss=protective_stop,
                take_profit1=take_profit1,
                take_profit2=take_profit2,
                risk_reward=risk_reward,
                thesis=f"Exit {context.symbol} because the session is too close to the bell to keep carrying a day trade.",
                invalidation="The day-trading plan does not want to hold this setup into or through the close.",
                next_watch=f"Flatten {context.symbol} before the close and only reconsider it tomorrow if the setup rebuilds.",
                reasons=[
                    "This workflow is now day-trading-first, so open positions should not be carried into the close by default.",
                    f"The current market phase is {context.market_clock.phase.replace('_', ' ')}."
                ],
                warnings=context.portfolio.warnings + ["Day-trading flatten rule is active near the close."],
                entry_rules=[
                    SignalRule(label="Duplicate entry", status="blocked", detail="A position already exists, so no new entry should be added."),
                    SignalRule(label="Session window", status="blocked", detail=f"The session phase is {context.market_clock.phase.replace('_', ' ')}."),
                    SignalRule(label="Risk budget", status="met", detail=f"Current position size is {_percent(_symbol_concentration_pct(position))}.")
                ],
                exit_rules=[
                    SignalRule(label="End-of-day flatten", status="triggered", detail="Flatten before the session ends."),
                    SignalRule(label="Protective stop", status="watch", detail=f"Protect the trade at {_price(protective_stop)} until it is closed."),
                    SignalRule(label="Signal quality", status="triggered", detail="The setup is no longer worth carrying into the close.")
                ]
            )

        if stop_hit or features.breakout_state == "failed_breakout" or features.trend_alignment == "bearish":
            return SetupCandidate(
                setup_type="failed_breakout" if features.breakout_state == "failed_breakout" else "no_trade",
                action="EXIT",
                entry_state="manage_position",
                strategy_type="Protective exit",
                timeframe="Intraday risk management",
                is_actionable=True,
                score=84,
                trigger_price=None,
                entry_price=position.average_cost,
                stop_loss=protective_stop,
                take_profit1=take_profit1,
                take_profit2=take_profit2,
                risk_reward=risk_reward,
                thesis=f"Exit {context.symbol} because the current intraday structure no longer justifies holding the long.",
                invalidation=f"The long is invalid once price loses {_price(protective_stop)} or fails the breakout structure.",
                next_watch=f"Do not re-enter {context.symbol} unless it rebuilds above VWAP and the prior breakdown level.",
                reasons=[
                    f"Price is too close to the protective stop at {_price(protective_stop)}.",
                    f"Trend alignment is {features.trend_alignment} and breakout state is {features.breakout_state.replace('_', ' ')}.",
                    f"You already hold {position.quantity} shares, so defense matters more than fresh conviction."
                ],
                warnings=context.portfolio.warnings + ["Protective exit takes priority over a duplicate entry."],
                entry_rules=[
                    SignalRule(label="Duplicate entry", status="blocked", detail="A position already exists."),
                    SignalRule(label="Trend support", status="blocked", detail=f"Trend alignment is {features.trend_alignment}."),
                    SignalRule(label="Risk budget", status="met", detail=f"Current position size is {_percent(_symbol_concentration_pct(position))}.")
                ],
                exit_rules=[
                    SignalRule(label="Protective stop", status="triggered", detail=f"Exit if price loses {_price(protective_stop)}."),
                    SignalRule(label="Failed breakout", status="triggered" if features.breakout_state == "failed_breakout" else "watch", detail="Breakout structure has failed."),
                    SignalRule(label="End-of-day flatten", status="watch", detail="Flatten later in the session if the trade is still open.")
                ]
            )

        if target1_hit or (gain_pct >= 1.2 and context.market_clock.phase == "power_hour"):
            return SetupCandidate(
                setup_type="pullback_continuation",
                action="REDUCE",
                entry_state="manage_position",
                strategy_type="Take partials",
                timeframe="Intraday risk management",
                is_actionable=True,
                score=74,
                trigger_price=None,
                entry_price=position.average_cost,
                stop_loss=protective_stop,
                take_profit1=take_profit1,
                take_profit2=take_profit2,
                risk_reward=risk_reward,
                thesis=f"Reduce {context.symbol} because the trade has already paid enough for the day that risk should now come down.",
                invalidation=f"If price keeps extending, only trail the remainder while it stays above {_price(protective_stop)}.",
                next_watch=f"Trim into strength around {_price(take_profit1)} and trail the remainder under fresh 5-minute lows.",
                reasons=[
                    f"Price has already traveled enough toward the intraday target ladder to justify paying yourself.",
                    f"Open P&L is {gain_pct:.2f}% versus the average cost."
                ],
                warnings=context.portfolio.warnings,
                entry_rules=[
                    SignalRule(label="Duplicate entry", status="blocked", detail="A position already exists."),
                    SignalRule(label="Target ladder", status="met", detail=f"Price is into the target area near {_price(take_profit1)}."),
                    SignalRule(label="Risk budget", status="met", detail=f"Current position size is {_percent(_symbol_concentration_pct(position))}.")
                ],
                exit_rules=[
                    SignalRule(label="Protective stop", status="watch", detail=f"Trail the remainder under {_price(protective_stop)}."),
                    SignalRule(label="Target 1", status="triggered", detail=f"Take partial profits near {_price(take_profit1)}."),
                    SignalRule(label="End-of-day flatten", status="watch", detail="Flatten any remainder before the bell.")
                ],
                trailing_stop=SignalTrailingStop(
                    enabled=True,
                    activation_price=round(take_profit1, 2),
                    trail_percent=0.6,
                    detail="Once the first target prints, trail under fresh 5-minute higher lows rather than giving the trade full room again."
                )
            )

        return SetupCandidate(
            setup_type="pullback_continuation" if features.trend_alignment == "bullish" else "no_trade",
            action="HOLD",
            entry_state="manage_position",
            strategy_type="Manage open trade",
            timeframe="Intraday risk management",
            is_actionable=False,
            score=62,
            trigger_price=None,
            entry_price=position.average_cost,
            stop_loss=protective_stop,
            take_profit1=take_profit1,
            take_profit2=take_profit2,
            risk_reward=risk_reward,
            thesis=f"Hold {context.symbol} for now because the trade is still above its intraday stop and has not yet earned a trim or exit.",
            invalidation=f"Exit if {context.symbol} loses {_price(protective_stop)} or if the breakout structure fails.",
            next_watch=f"Keep holding while {context.symbol} stays above {_price(protective_stop)}. Trim only after a cleaner push toward {_price(take_profit1)}.",
            reasons=[
                f"The position is still above its protective stop at {_price(protective_stop)}.",
                f"Trend alignment remains {features.trend_alignment}, which does not yet justify an exit."
            ],
            warnings=context.portfolio.warnings,
            entry_rules=[
                SignalRule(label="Duplicate entry", status="blocked", detail="A position already exists, so no add is allowed right now."),
                SignalRule(label="Trend support", status="met" if features.trend_alignment == "bullish" else "watch", detail=f"Trend alignment is {features.trend_alignment}."),
                SignalRule(label="Risk budget", status="met", detail=f"Current position size is {_percent(_symbol_concentration_pct(position))}.")
            ],
            exit_rules=[
                SignalRule(label="Protective stop", status="watch", detail=f"Exit if price loses {_price(protective_stop)}."),
                SignalRule(label="Target 1", status="watch", detail=f"Trim near {_price(take_profit1)}."),
                SignalRule(label="End-of-day flatten", status="watch", detail="Flatten before the bell if the position is still open.")
            ]
        )

    def _no_trade(self, context: SignalContext) -> SetupCandidate:
        features = context.features.snapshot
        reasons = [
            f"{context.symbol} does not currently have a clean intraday setup that clears the day-trading bar.",
            f"Breakout state is {features.breakout_state.replace('_', ' ')} with trend alignment {features.trend_alignment}.",
            f"Relative volume is {features.relative_volume:.2f}x and session range is {features.session_range_pct:.2f}%."
        ]
        warnings = list(context.portfolio.warnings)
        if context.watchlist_item is None and context.position is None:
            warnings.append("The engine is monitoring this symbol from the default universe, not because it is already on your watchlist.")
        return _stand_aside_candidate(
            context,
            reasons=reasons,
            warnings=warnings,
            next_watch=(
                f"Wait for {context.symbol} to either break the opening range cleanly, reclaim VWAP with follow-through, "
                "or build a cleaner pullback continuation before treating it as a live day trade."
            )
        )


def _sort_key(signal: TradingSignalRecord) -> tuple[int, int, int, str]:
    action_priority = {
        "EXIT": 0,
        "REDUCE": 1,
        "BUY": 2,
        "SELL": 3,
        "HOLD": 4,
        "NO_TRADE": 5
    }
    return (
        0 if signal.is_actionable else 1,
        action_priority[signal.action],
        -signal.score,
        signal.symbol
    )


def _alerts(items: list[TradingSignalRecord], overview: MarketOverviewResponse) -> list[SignalAlert]:
    alerts: list[SignalAlert] = []
    timestamp = _now()

    if overview.clock.phase in {"opening_range", "near_close"}:
        alerts.append(
            SignalAlert(
                id="regime-change",
                type="regime_change",
                symbol=None,
                severity="caution",
                title="Session phase matters right now",
                message="Opening-range and near-close periods can change setup quality quickly, so treat stale signals with caution.",
                timestamp=timestamp
            )
        )

    for item in items:
        if item.action == "BUY" and item.is_actionable and not item.has_position:
            alerts.append(
                SignalAlert(
                    id=f"{item.symbol}-new-buy",
                    type="new_actionable_setup",
                    symbol=item.symbol,
                    severity="info",
                    title=f"New BUY signal for {item.symbol}",
                    message=f"Entry is live around {item.entry_zone or _price(item.entry_price)}.",
                    timestamp=timestamp
                )
            )

        if item.action == "EXIT" and item.has_position:
            alerts.append(
                SignalAlert(
                    id=f"{item.symbol}-exit",
                    type="exit_signal",
                    symbol=item.symbol,
                    severity="risk",
                    title=f"EXIT signal for {item.symbol}",
                    message=f"The open trade should come off around {_price(item.stop_loss)} or because the session window is ending.",
                    timestamp=timestamp
                )
            )

        if item.current_position is not None and item.stop_loss is not None and item.current_position.market_price <= item.stop_loss * 1.005:
            alerts.append(
                SignalAlert(
                    id=f"{item.symbol}-stop-hit",
                    type="stop_breach",
                    symbol=item.symbol,
                    severity="risk",
                    title=f"Stop framework under pressure in {item.symbol}",
                    message=f"Price is pressing the stop area near {_price(item.stop_loss)}.",
                    timestamp=timestamp
                )
            )

        if item.current_position is not None and item.take_profit1 is not None and item.current_position.market_price >= item.take_profit1:
            alerts.append(
                SignalAlert(
                    id=f"{item.symbol}-target-hit",
                    type="target_hit",
                    symbol=item.symbol,
                    severity="info",
                    title=f"First target reached in {item.symbol}",
                    message=f"Price has reached {_price(item.take_profit1)} and should be managed tighter for the rest of the day.",
                    timestamp=timestamp
                )
            )

        if item.has_position and item.action in {"REDUCE", "EXIT"}:
            alerts.append(
                SignalAlert(
                    id=f"{item.symbol}-downgrade",
                    type="signal_downgrade",
                    symbol=item.symbol,
                    severity="caution",
                    title=f"Signal downgraded for {item.symbol}",
                    message="The open position moved from normal management into active defense.",
                    timestamp=timestamp
                )
            )

    return alerts[:8]


def _focus(items: list[TradingSignalRecord], portfolio: SignalPortfolioState) -> SignalFocus:
    if not items:
        return SignalFocus(
            headline="No symbols in scope",
            summary="Add watchlist names before the intraday engine can score anything relevant.",
            symbol=None,
            action=None,
            next_steps=["Add a symbol to the watchlist to start getting intraday decision support."],
            warnings=portfolio.warnings[:2]
        )

    primary = items[0]
    if primary.is_actionable:
        action_verb = {
            "BUY": "Buy",
            "SELL": "Sell",
            "EXIT": "Exit",
            "REDUCE": "Reduce",
            "HOLD": "Hold",
            "NO_TRADE": "Stand aside"
        }[primary.action]
        return SignalFocus(
            headline=f"{action_verb} {primary.symbol} now",
            summary=primary.thesis,
            symbol=primary.symbol,
            action=primary.action,
            next_steps=[
                primary.next_watch,
                f"Protect the setup at {_price(primary.stop_loss)}.",
                f"Work the first target near {_price(primary.take_profit1)}."
            ],
            warnings=(primary.warnings + portfolio.warnings)[:3]
        )

    if primary.action == "NO_TRADE":
        return SignalFocus(
            headline="Stand aside right now",
            summary=primary.thesis,
            symbol=primary.symbol,
            action=primary.action,
            next_steps=[
                primary.next_watch,
                "Do nothing until the trigger level and confirmation conditions are both clean."
            ],
            warnings=(primary.warnings + portfolio.warnings)[:3]
        )

    return SignalFocus(
        headline="Manage what you already hold",
        summary=primary.thesis,
        symbol=primary.symbol,
        action=primary.action,
        next_steps=[primary.next_watch],
        warnings=(primary.warnings + portfolio.warnings)[:3]
    )


def get_signals(
    session: DatabaseSession,
    request_session: SessionResponse,
    current_session: AuthenticatedSessionContext | None
) -> SignalsResponse:
    market_clock = get_market_clock()
    market_overview = get_market_overview()
    risk_snapshot = get_risk_snapshot(request_session)

    watchlist_items: dict[str, WatchlistItemRecord] = {}
    positions_by_symbol: dict[str, PaperPositionRecord] = {}
    portfolio_summary: PaperPortfolioSummary | None = None
    daily_realized_pnl = 0.0

    if current_session is not None:
        watchlist_snapshot = list_watchlist(session, current_session)
        watchlist_items = {item.symbol: item for item in watchlist_snapshot.items}
        positions_snapshot = list_open_positions(session, current_session)
        positions_by_symbol = {item.symbol: item for item in positions_snapshot.items}
        portfolio_summary = get_portfolio_summary(session, current_session)
        daily_realized_pnl = PaperTradingRepository(session).get_realized_pnl_since(
            current_session.user_id,
            _eastern_day_start_iso()
        )

    portfolio = _portfolio_state(
        portfolio_summary,
        risk_snapshot,
        market_clock,
        daily_realized_pnl
    )

    universe: list[str] = []
    for symbol in [*positions_by_symbol.keys(), *watchlist_items.keys(), *DEFAULT_SIGNAL_UNIVERSE]:
        if symbol not in universe:
            universe.append(symbol)

    engine: SignalEngine = RuleBasedIntradaySignalEngine()
    items = []
    for symbol in universe:
        quote = get_quote_snapshot(symbol)
        execution_candles = get_intraday_candle_history(symbol, "5min", 96)
        confirmation_candles = get_intraday_candle_history(symbol, "15min", 64)
        features = build_intraday_features(
            quote=quote,
            execution_candles=execution_candles,
            confirmation_candles=confirmation_candles,
            market_clock=market_clock
        )
        items.append(
            engine.evaluate(
                SignalContext(
                    symbol=symbol,
                    quote=quote,
                    features=features,
                    watchlist_item=watchlist_items.get(symbol),
                    position=positions_by_symbol.get(symbol),
                    market_overview=market_overview,
                    market_clock=market_clock,
                    risk_snapshot=risk_snapshot,
                    portfolio=portfolio
                )
            )
        )

    sorted_items = sorted(items, key=_sort_key)
    qualities = {item.market_data_quality for item in sorted_items}
    sources = {item.market_data_source for item in sorted_items}
    if not sorted_items:
        aggregate_quality = market_overview.quality
        aggregate_source = market_overview.source
    elif len(qualities) == 1 and market_overview.quality in qualities:
        aggregate_quality = next(iter(qualities))
        aggregate_source = next(iter(sources))
    else:
        aggregate_quality = "mixed"
        aggregate_source = "mixed-market-data"

    if current_session is not None:
        persist_signal_run(
            session,
            current_session,
            market_clock=market_clock,
            regime_headline=market_overview.regime.headline,
            items=sorted_items
        )
        alerts = list_signal_alerts(
            session,
            current_session,
            limit=8,
            minutes=240
        ).items
    else:
        alerts = _alerts(sorted_items, market_overview)

    return SignalsResponse(
        as_of=_now(),
        source=SIGNAL_SOURCE,
        market_data_source=aggregate_source,
        market_data_quality=aggregate_quality,
        market_clock=market_clock,
        regime_headline=market_overview.regime.headline,
        portfolio=portfolio,
        focus=_focus(sorted_items, portfolio),
        alerts=alerts,
        items=sorted_items
    )
