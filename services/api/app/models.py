from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

CandleInterval = Literal["1min", "5min", "15min", "1day"]
MarketClockPhase = Literal[
    "premarket",
    "opening_range",
    "midday",
    "power_hour",
    "near_close",
    "after_hours",
    "closed"
]
SignalAction = Literal["BUY", "SELL", "HOLD", "EXIT", "REDUCE", "NO_TRADE"]
SignalSetupType = Literal[
    "opening_range_breakout",
    "vwap_reclaim",
    "pullback_continuation",
    "failed_breakout",
    "no_trade"
]
SignalEntryState = Literal[
    "enter_now",
    "wait_for_confirmation",
    "manage_position",
    "stand_aside"
]
SignalChangeType = Literal[
    "initial_snapshot",
    "new_actionable_setup",
    "setup_confirmed",
    "signal_downgrade",
    "exit_signal",
    "stop_breach",
    "target_hit",
    "near_close_flatten_warning",
    "fallback_data_warning",
    "setup_changed",
    "action_changed",
    "confidence_changed",
    "level_changed",
    "signal_invalidated",
    "session_changed",
    "regime_changed"
]
SignalAlertStatus = Literal["new", "read", "acknowledged"]


class Greeks(BaseModel):
    delta: float
    gamma: float
    vega: float
    theta: float


class Opportunity(BaseModel):
    id: str
    symbol: str
    structure: str
    thesis: str
    dte: int = Field(ge=0)
    score: int = Field(ge=0, le=100)
    expected_return: float
    expected_shortfall: float
    win_rate: float = Field(ge=0, le=100)
    spread_bps: int = Field(ge=0)
    max_loss: float
    catalysts: list[str]
    top_drivers: list[str]
    greeks: Greeks


class OpportunitiesResponse(BaseModel):
    as_of: datetime
    source: str
    items: list[Opportunity]


class ScenarioRow(BaseModel):
    move: str
    pnl: tuple[float, float, float]


class TradeDetail(BaseModel):
    id: str
    symbol: str
    structure: str
    thesis: str
    score: int
    dte: int = Field(ge=0)
    iv_rank: int = Field(ge=0, le=100)
    spread_bps: int = Field(ge=0)
    expected_return: float
    max_loss: float
    expected_shortfall: float
    greeks: Greeks
    payoff: list[float]
    scenario: list[ScenarioRow]
    notes: list[str]


class RiskMetric(BaseModel):
    label: str
    current: float
    limit: float
    unit: str


class ExposureBucket(BaseModel):
    bucket: str
    value: int


class RiskSnapshot(BaseModel):
    execution_mode: Literal["paper", "live"]
    entitlement: str
    metrics: list[RiskMetric]
    concentration: list[ExposureBucket]


class SessionUser(BaseModel):
    id: str
    handle: str
    name: str


class SessionResponse(BaseModel):
    mode: Literal["anonymous", "development", "authenticated"]
    is_authenticated: bool
    user: SessionUser | None = None
    entitlement: str
    execution_mode: Literal["paper", "live"]
    session_strategy: Literal["development", "local-token", "external"]
    requires_local_token: bool
    expires_at: datetime | None = None


class SessionCreateRequest(BaseModel):
    handle: str = Field(
        min_length=2,
        max_length=32,
        pattern=r"^[a-z0-9][a-z0-9._-]{1,31}$"
    )
    display_name: str | None = Field(default=None, min_length=2, max_length=60)
    access_token: str | None = Field(default=None, max_length=128)


class MarketRegime(BaseModel):
    headline: str
    summary: str
    volatility_regime: str
    breadth_regime: str


class MarketBenchmark(BaseModel):
    symbol: str
    move_pct: float
    note: str


class MarketEvent(BaseModel):
    label: str
    scheduled_at: str
    impact: Literal["low", "medium", "high"]


class MarketClock(BaseModel):
    is_open: bool
    session: Literal["pre", "regular", "post", "closed"]
    phase: MarketClockPhase
    as_of: datetime
    next_open: str | None = None
    next_close: str | None = None
    minutes_since_open: int | None = Field(default=None, ge=0)
    minutes_to_close: int | None = Field(default=None, ge=0)
    source: str
    quality: Literal["provider", "fallback"]


class MarketOverviewResponse(BaseModel):
    as_of: datetime
    source: str
    quality: Literal["provider", "fallback"]
    clock: MarketClock
    regime: MarketRegime
    benchmarks: list[MarketBenchmark]
    highlights: list[str]
    upcoming_events: list[MarketEvent]


class SymbolSearchResult(BaseModel):
    symbol: str
    name: str
    exchange: str
    asset_type: str
    region: str
    currency: str
    match_score: float | None = None
    source: str
    quality: Literal["provider", "fallback"]


class SymbolSearchResponse(BaseModel):
    as_of: datetime
    query: str
    source: str
    quality: Literal["provider", "fallback"]
    items: list[SymbolSearchResult]


class CandleRecord(BaseModel):
    symbol: str
    interval: CandleInterval
    timestamp: datetime
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: int = Field(ge=0)
    source: str
    quality: Literal["provider", "fallback"]


class CandleHistoryResponse(BaseModel):
    as_of: datetime
    symbol: str
    interval: CandleInterval
    source: str
    quality: Literal["provider", "fallback"]
    items: list[CandleRecord]


class ExplanationDriver(BaseModel):
    title: str
    detail: str


class ExplanationWarning(BaseModel):
    severity: Literal["info", "caution", "risk"]
    title: str
    detail: str


class TradeExplanation(BaseModel):
    trade_id: str
    headline: str
    summary: str
    drivers: list[ExplanationDriver]
    warnings: list[ExplanationWarning]


class HealthResponse(BaseModel):
    status: str
    environment: str
    provider: str


class QuoteSnapshot(BaseModel):
    symbol: str
    last: float = Field(gt=0)
    change: float
    change_percent: float
    previous_close: float | None = Field(default=None, gt=0)
    as_of: datetime
    source: str
    quality: Literal["provider", "fallback"]


class WatchlistItemUpsertRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=16)
    notes: str | None = Field(default=None, max_length=280)


class WatchlistItemRecord(BaseModel):
    symbol: str
    notes: str | None = None
    added_at: datetime
    updated_at: datetime
    quote: QuoteSnapshot


class WatchlistResponse(BaseModel):
    as_of: datetime
    watchlist_id: str
    items: list[WatchlistItemRecord]


class WatchlistDeleteResponse(BaseModel):
    removed: bool
    symbol: str


class PaperExecutionAssumptions(BaseModel):
    fill_model: str
    price_source: str
    commissions: str
    sells_require_existing_position: bool


class PaperOrderRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=16)
    side: Literal["buy", "sell"]
    quantity: int = Field(gt=0, le=100_000)
    order_type: Literal["market"] = "market"


class PaperOrderRecord(BaseModel):
    id: str
    symbol: str
    side: Literal["buy", "sell"]
    quantity: int = Field(gt=0)
    order_type: Literal["market"]
    status: Literal["filled", "rejected"]
    requested_price: float = Field(gt=0)
    fill_price: float | None = Field(default=None, gt=0)
    submitted_at: datetime
    filled_at: datetime | None = None
    rejection_reason: str | None = None


class PaperFillRecord(BaseModel):
    id: str
    order_id: str
    symbol: str
    side: Literal["buy", "sell"]
    quantity: int = Field(gt=0)
    market_price: float = Field(gt=0)
    fill_price: float = Field(gt=0)
    realized_pnl: float
    filled_at: datetime


class PaperPositionRecord(BaseModel):
    symbol: str
    quantity: int = Field(gt=0)
    average_cost: float = Field(ge=0)
    market_price: float = Field(gt=0)
    market_value: float
    cost_basis: float
    realized_pnl: float
    unrealized_pnl: float
    total_pnl: float
    market_source: str
    market_quality: Literal["provider", "fallback"]
    updated_at: datetime


class PaperPositionsResponse(BaseModel):
    as_of: datetime
    items: list[PaperPositionRecord]


class PaperOrdersResponse(BaseModel):
    as_of: datetime
    items: list[PaperOrderRecord]


class PaperPortfolioSummary(BaseModel):
    as_of: datetime
    positions: int
    gross_exposure: float
    market_value: float
    cost_basis: float
    realized_pnl: float
    unrealized_pnl: float
    total_pnl: float
    market_data_source: str
    market_data_quality: Literal["provider", "fallback", "mixed"]
    assumptions: PaperExecutionAssumptions


class PaperOrderPlacementResponse(BaseModel):
    order: PaperOrderRecord
    fill: PaperFillRecord | None = None
    position: PaperPositionRecord | None = None
    portfolio: PaperPortfolioSummary
    assumptions: PaperExecutionAssumptions


class SignalRule(BaseModel):
    label: str
    status: Literal["met", "watch", "blocked", "triggered"]
    detail: str


class SignalTrailingStop(BaseModel):
    enabled: bool
    activation_price: float | None = Field(default=None, gt=0)
    trail_percent: float | None = Field(default=None, gt=0)
    detail: str


class IntradayFeatureSnapshot(BaseModel):
    execution_interval: Literal["1min", "5min"]
    confirmation_interval: Literal["15min"]
    session_phase: MarketClockPhase
    opening_range_high: float | None = Field(default=None, gt=0)
    opening_range_low: float | None = Field(default=None, gt=0)
    session_high: float | None = Field(default=None, gt=0)
    session_low: float | None = Field(default=None, gt=0)
    vwap: float | None = Field(default=None, gt=0)
    momentum_5m_pct: float
    momentum_15m_pct: float
    pullback_depth_pct: float = Field(ge=0)
    relative_volume: float = Field(ge=0)
    session_range_pct: float = Field(ge=0)
    trend_alignment: Literal["bullish", "bearish", "mixed"]
    breakout_state: Literal[
        "above_range",
        "below_range",
        "inside_range",
        "failed_breakout",
        "failed_breakdown"
    ]
    distance_to_stop_pct: float | None = Field(default=None, ge=0)


class TradingSignalRecord(BaseModel):
    symbol: str
    action: SignalAction
    confidence: int = Field(ge=0, le=100)
    score: int = Field(ge=0, le=100)
    setup_type: SignalSetupType
    entry_state: SignalEntryState
    strategy_type: str
    timeframe: str
    thesis: str
    trigger_price: float | None = Field(default=None, gt=0)
    entry_price: float | None = Field(default=None, gt=0)
    entry_zone: str | None = None
    stop_loss: float | None = Field(default=None, gt=0)
    take_profit1: float | None = Field(default=None, gt=0)
    take_profit2: float | None = Field(default=None, gt=0)
    invalidation: str
    risk_reward: float | None = Field(default=None, gt=0)
    position_size_pct: float = Field(ge=0, le=100)
    reasons: list[str]
    warnings: list[str]
    timestamp: datetime
    is_actionable: bool
    has_position: bool
    market_data_source: str
    market_data_quality: Literal["provider", "fallback"]
    current_position: PaperPositionRecord | None = None
    opportunity_id: str | None = None
    next_watch: str
    entry_rules: list[SignalRule]
    exit_rules: list[SignalRule]
    trailing_stop: SignalTrailingStop | None = None
    intraday_features: IntradayFeatureSnapshot


class SignalPortfolioState(BaseModel):
    capital_base: float = Field(gt=0)
    gross_exposure: float = Field(ge=0)
    gross_exposure_pct: float = Field(ge=0, le=100)
    available_exposure_pct: float = Field(ge=0, le=100)
    max_total_exposure_pct: float = Field(gt=0, le=100)
    max_risk_per_trade_pct: float = Field(gt=0, le=100)
    max_daily_loss_pct: float = Field(gt=0, le=100)
    max_open_positions: int = Field(ge=1)
    max_symbol_concentration_pct: float = Field(gt=0, le=100)
    open_positions: int = Field(ge=0)
    risk_utilization_pct: float = Field(ge=0)
    daily_pnl: float
    daily_pnl_pct: float
    daily_loss_limit_hit: bool
    flatten_before_close: bool
    warnings: list[str]


class SignalFocus(BaseModel):
    headline: str
    summary: str
    symbol: str | None = None
    action: SignalAction | None = None
    next_steps: list[str]
    warnings: list[str]


class SignalChangeRecord(BaseModel):
    type: SignalChangeType
    summary: str
    detail: str
    previous_value: str | None = None
    current_value: str | None = None
    is_material: bool = True


class SignalTransitionSummary(BaseModel):
    has_meaningful_change: bool
    headline: str | None = None
    changes: list[SignalChangeRecord]


class SignalAlert(BaseModel):
    id: str
    type: Literal[
        "new_actionable_setup",
        "setup_confirmed",
        "exit_signal",
        "stop_breach",
        "target_hit",
        "signal_downgrade",
        "near_close_flatten_warning",
        "fallback_data_warning",
        "regime_change"
    ]
    symbol: str | None = None
    severity: Literal["info", "caution", "risk"]
    title: str
    message: str
    timestamp: datetime
    status: SignalAlertStatus = "new"
    snapshot_id: str | None = None
    change_types: list[SignalChangeType] = Field(default_factory=list)
    data_quality: Literal["provider", "fallback", "mixed"] | None = None
    read_at: datetime | None = None
    acknowledged_at: datetime | None = None


class SignalSnapshotRecord(TradingSignalRecord):
    snapshot_id: str
    snapshot_at: datetime
    market_phase: MarketClockPhase
    regime_headline: str
    transition: SignalTransitionSummary | None = None


class SignalHistoryResponse(BaseModel):
    as_of: datetime
    symbol: str
    items: list[SignalSnapshotRecord]


class SignalAlertsResponse(BaseModel):
    as_of: datetime
    items: list[SignalAlert]


class SignalAlertStatusUpdateRequest(BaseModel):
    status: Literal["read", "acknowledged"]


class SignalScorecardItem(BaseModel):
    symbol: str
    setup_type: SignalSetupType
    action: SignalAction
    triggered_at: datetime
    outcome: Literal["target_hit", "stop_hit", "exit_signal", "open", "no_resolution"]
    alert_count: int = Field(ge=0)
    alert_types: list[str]
    market_phase: MarketClockPhase
    market_data_quality: Literal["provider", "fallback"]
    entry_price: float | None = Field(default=None, gt=0)
    stop_loss: float | None = Field(default=None, gt=0)
    take_profit1: float | None = Field(default=None, gt=0)
    notes: list[str]


class SignalSetupScorecardStat(BaseModel):
    setup_type: SignalSetupType
    total: int = Field(ge=0)
    target_hits: int = Field(ge=0)
    stop_hits: int = Field(ge=0)
    exit_signals: int = Field(ge=0)
    open: int = Field(ge=0)
    no_resolution: int = Field(ge=0)
    win_rate_pct: float = Field(ge=0, le=100)


class IntradayScorecardResponse(BaseModel):
    as_of: datetime
    session_date: str
    lookback_days: int = Field(ge=1, le=5)
    symbols_with_snapshots: int = Field(ge=0)
    actionable_signals: int = Field(ge=0)
    alerts_fired: int = Field(ge=0)
    fallback_alerts: int = Field(ge=0)
    items: list[SignalScorecardItem]
    setup_stats: list[SignalSetupScorecardStat]


class SignalsResponse(BaseModel):
    as_of: datetime
    source: str
    market_data_source: str
    market_data_quality: Literal["provider", "fallback", "mixed"]
    market_clock: MarketClock
    regime_headline: str
    portfolio: SignalPortfolioState
    focus: SignalFocus
    alerts: list[SignalAlert]
    items: list[TradingSignalRecord]
