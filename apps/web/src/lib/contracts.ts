export interface Greeks {
  delta: number;
  gamma: number;
  vega: number;
  theta: number;
}

export interface OpportunityRecord {
  id: string;
  symbol: string;
  structure: string;
  thesis: string;
  dte: number;
  score: number;
  expected_return: number;
  expected_shortfall: number;
  win_rate: number;
  spread_bps: number;
  max_loss: number;
  catalysts: string[];
  top_drivers: string[];
  greeks: Greeks;
}

export interface OpportunitiesResponse {
  as_of: string;
  source: string;
  items: OpportunityRecord[];
}

export interface ScenarioRow {
  move: string;
  pnl: [number, number, number];
}

export interface TradeDetailResponse {
  id: string;
  symbol: string;
  structure: string;
  thesis: string;
  score: number;
  dte: number;
  iv_rank: number;
  spread_bps: number;
  expected_return: number;
  max_loss: number;
  expected_shortfall: number;
  greeks: Greeks;
  payoff: number[];
  scenario: ScenarioRow[];
  notes: string[];
}

export interface RiskMetric {
  label: string;
  current: number;
  limit: number;
  unit: string;
}

export interface ExposureBucket {
  bucket: string;
  value: number;
}

export interface RiskSnapshot {
  execution_mode: "paper" | "live";
  entitlement: string;
  metrics: RiskMetric[];
  concentration: ExposureBucket[];
}

export interface SessionUser {
  id: string;
  handle: string;
  name: string;
}

export interface SessionResponse {
  mode: "anonymous" | "development" | "authenticated";
  is_authenticated: boolean;
  user: SessionUser | null;
  entitlement: string;
  execution_mode: "paper" | "live";
  session_strategy: "development" | "local-token" | "external";
  requires_local_token: boolean;
  expires_at: string | null;
}

export interface SessionCreateRequest {
  handle: string;
  display_name?: string | null;
  access_token?: string | null;
}

export interface MarketRegime {
  headline: string;
  summary: string;
  volatility_regime: string;
  breadth_regime: string;
}

export interface MarketBenchmark {
  symbol: string;
  move_pct: number;
  note: string;
}

export interface MarketEvent {
  label: string;
  scheduled_at: string;
  impact: "low" | "medium" | "high";
}

export interface MarketClock {
  is_open: boolean;
  session: "pre" | "regular" | "post" | "closed";
  phase:
    | "premarket"
    | "opening_range"
    | "midday"
    | "power_hour"
    | "near_close"
    | "after_hours"
    | "closed";
  as_of: string;
  next_open: string | null;
  next_close: string | null;
  minutes_since_open: number | null;
  minutes_to_close: number | null;
  source: string;
  quality: "provider" | "fallback";
}

export interface MarketOverviewResponse {
  as_of: string;
  source: string;
  quality: "provider" | "fallback";
  clock: MarketClock;
  regime: MarketRegime;
  benchmarks: MarketBenchmark[];
  highlights: string[];
  upcoming_events: MarketEvent[];
}

export interface SymbolSearchResult {
  symbol: string;
  name: string;
  exchange: string;
  asset_type: string;
  region: string;
  currency: string;
  match_score: number | null;
  source: string;
  quality: "provider" | "fallback";
}

export interface SymbolSearchResponse {
  as_of: string;
  query: string;
  source: string;
  quality: "provider" | "fallback";
  items: SymbolSearchResult[];
}

export interface CandleRecord {
  symbol: string;
  interval: "1min" | "5min" | "15min" | "1day";
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  source: string;
  quality: "provider" | "fallback";
}

export interface CandleHistoryResponse {
  as_of: string;
  symbol: string;
  interval: "1min" | "5min" | "15min" | "1day";
  source: string;
  quality: "provider" | "fallback";
  items: CandleRecord[];
}

export interface ExplanationDriver {
  title: string;
  detail: string;
}

export interface ExplanationWarning {
  severity: "info" | "caution" | "risk";
  title: string;
  detail: string;
}

export interface TradeExplanationResponse {
  trade_id: string;
  headline: string;
  summary: string;
  drivers: ExplanationDriver[];
  warnings: ExplanationWarning[];
}

export interface QuoteSnapshot {
  symbol: string;
  last: number;
  change: number;
  change_percent: number;
  previous_close: number | null;
  as_of: string;
  source: string;
  quality: "provider" | "fallback";
}

export interface WatchlistItemUpsertRequest {
  symbol: string;
  notes?: string | null;
}

export interface WatchlistItemRecord {
  symbol: string;
  notes: string | null;
  added_at: string;
  updated_at: string;
  quote: QuoteSnapshot;
}

export interface WatchlistResponse {
  as_of: string;
  watchlist_id: string;
  items: WatchlistItemRecord[];
}

export interface WatchlistDeleteResponse {
  removed: boolean;
  symbol: string;
}

export interface PaperExecutionAssumptions {
  fill_model: string;
  price_source: string;
  commissions: string;
  sells_require_existing_position: boolean;
}

export interface PaperOrderRequest {
  symbol: string;
  side: "buy" | "sell";
  quantity: number;
  order_type?: "market";
}

export interface PaperOrderRecord {
  id: string;
  symbol: string;
  side: "buy" | "sell";
  quantity: number;
  order_type: "market";
  status: "filled" | "rejected";
  requested_price: number;
  fill_price: number | null;
  submitted_at: string;
  filled_at: string | null;
  rejection_reason: string | null;
}

export interface PaperFillRecord {
  id: string;
  order_id: string;
  symbol: string;
  side: "buy" | "sell";
  quantity: number;
  market_price: number;
  fill_price: number;
  realized_pnl: number;
  filled_at: string;
}

export interface PaperPositionRecord {
  symbol: string;
  quantity: number;
  average_cost: number;
  market_price: number;
  market_value: number;
  cost_basis: number;
  realized_pnl: number;
  unrealized_pnl: number;
  total_pnl: number;
  market_source: string;
  market_quality: "provider" | "fallback";
  updated_at: string;
}

export interface PaperPositionsResponse {
  as_of: string;
  items: PaperPositionRecord[];
}

export interface PaperOrdersResponse {
  as_of: string;
  items: PaperOrderRecord[];
}

export interface PaperPortfolioSummary {
  as_of: string;
  positions: number;
  gross_exposure: number;
  market_value: number;
  cost_basis: number;
  realized_pnl: number;
  unrealized_pnl: number;
  total_pnl: number;
  market_data_source: string;
  market_data_quality: "provider" | "fallback" | "mixed";
  assumptions: PaperExecutionAssumptions;
}

export interface PaperOrderPlacementResponse {
  order: PaperOrderRecord;
  fill: PaperFillRecord | null;
  position: PaperPositionRecord | null;
  portfolio: PaperPortfolioSummary;
  assumptions: PaperExecutionAssumptions;
}

export interface SignalRule {
  label: string;
  status: "met" | "watch" | "blocked" | "triggered";
  detail: string;
}

export interface SignalTrailingStop {
  enabled: boolean;
  activation_price: number | null;
  trail_percent: number | null;
  detail: string;
}

export interface IntradayFeatureSnapshot {
  execution_interval: "1min" | "5min";
  confirmation_interval: "15min";
  session_phase:
    | "premarket"
    | "opening_range"
    | "midday"
    | "power_hour"
    | "near_close"
    | "after_hours"
    | "closed";
  opening_range_high: number | null;
  opening_range_low: number | null;
  session_high: number | null;
  session_low: number | null;
  vwap: number | null;
  momentum_5m_pct: number;
  momentum_15m_pct: number;
  pullback_depth_pct: number;
  relative_volume: number;
  session_range_pct: number;
  trend_alignment: "bullish" | "bearish" | "mixed";
  breakout_state:
    | "above_range"
    | "below_range"
    | "inside_range"
    | "failed_breakout"
    | "failed_breakdown";
  distance_to_stop_pct: number | null;
}

export interface TradingSignalRecord {
  symbol: string;
  action: "BUY" | "SELL" | "HOLD" | "EXIT" | "REDUCE" | "NO_TRADE";
  confidence: number;
  score: number;
  setup_type:
    | "opening_range_breakout"
    | "vwap_reclaim"
    | "pullback_continuation"
    | "failed_breakout"
    | "no_trade";
  entry_state: "enter_now" | "wait_for_confirmation" | "manage_position" | "stand_aside";
  strategy_type: string;
  timeframe: string;
  thesis: string;
  trigger_price: number | null;
  entry_price: number | null;
  entry_zone: string | null;
  stop_loss: number | null;
  take_profit1: number | null;
  take_profit2: number | null;
  invalidation: string;
  risk_reward: number | null;
  position_size_pct: number;
  reasons: string[];
  warnings: string[];
  timestamp: string;
  is_actionable: boolean;
  has_position: boolean;
  market_data_source: string;
  market_data_quality: "provider" | "fallback";
  current_position: PaperPositionRecord | null;
  opportunity_id: string | null;
  next_watch: string;
  entry_rules: SignalRule[];
  exit_rules: SignalRule[];
  trailing_stop: SignalTrailingStop | null;
  intraday_features: IntradayFeatureSnapshot;
}

export interface SignalPortfolioState {
  capital_base: number;
  gross_exposure: number;
  gross_exposure_pct: number;
  available_exposure_pct: number;
  max_total_exposure_pct: number;
  max_risk_per_trade_pct: number;
  max_daily_loss_pct: number;
  max_open_positions: number;
  max_symbol_concentration_pct: number;
  open_positions: number;
  risk_utilization_pct: number;
  daily_pnl: number;
  daily_pnl_pct: number;
  daily_loss_limit_hit: boolean;
  flatten_before_close: boolean;
  warnings: string[];
}

export interface SignalFocus {
  headline: string;
  summary: string;
  symbol: string | null;
  action: "BUY" | "SELL" | "HOLD" | "EXIT" | "REDUCE" | "NO_TRADE" | null;
  next_steps: string[];
  warnings: string[];
}

export interface SignalChangeRecord {
  type:
    | "initial_snapshot"
    | "new_actionable_setup"
    | "setup_confirmed"
    | "signal_downgrade"
    | "exit_signal"
    | "stop_breach"
    | "target_hit"
    | "near_close_flatten_warning"
    | "fallback_data_warning"
    | "setup_changed"
    | "action_changed"
    | "confidence_changed"
    | "level_changed"
    | "signal_invalidated"
    | "session_changed"
    | "regime_changed";
  summary: string;
  detail: string;
  previous_value: string | null;
  current_value: string | null;
  is_material: boolean;
}

export interface SignalTransitionSummary {
  has_meaningful_change: boolean;
  headline: string | null;
  changes: SignalChangeRecord[];
}

export interface SignalAlert {
  id: string;
  type:
    | "new_actionable_setup"
    | "setup_confirmed"
    | "exit_signal"
    | "stop_breach"
    | "target_hit"
    | "signal_downgrade"
    | "near_close_flatten_warning"
    | "fallback_data_warning"
    | "regime_change";
  symbol: string | null;
  severity: "info" | "caution" | "risk";
  title: string;
  message: string;
  timestamp: string;
  status: "new" | "read" | "acknowledged";
  snapshot_id: string | null;
  change_types: SignalChangeRecord["type"][];
  data_quality: "provider" | "fallback" | "mixed" | null;
  read_at: string | null;
  acknowledged_at: string | null;
}

export interface SignalSnapshotRecord extends TradingSignalRecord {
  snapshot_id: string;
  snapshot_at: string;
  market_phase:
    | "premarket"
    | "opening_range"
    | "midday"
    | "power_hour"
    | "near_close"
    | "after_hours"
    | "closed";
  regime_headline: string;
  transition: SignalTransitionSummary | null;
}

export interface SignalHistoryResponse {
  as_of: string;
  symbol: string;
  items: SignalSnapshotRecord[];
}

export interface SignalAlertsResponse {
  as_of: string;
  items: SignalAlert[];
}

export interface SignalAlertStatusUpdateRequest {
  status: "read" | "acknowledged";
}

export interface SignalScorecardItem {
  symbol: string;
  setup_type:
    | "opening_range_breakout"
    | "vwap_reclaim"
    | "pullback_continuation"
    | "failed_breakout"
    | "no_trade";
  action: "BUY" | "SELL" | "HOLD" | "EXIT" | "REDUCE" | "NO_TRADE";
  triggered_at: string;
  outcome: "target_hit" | "stop_hit" | "exit_signal" | "open" | "no_resolution";
  alert_count: number;
  alert_types: string[];
  market_phase:
    | "premarket"
    | "opening_range"
    | "midday"
    | "power_hour"
    | "near_close"
    | "after_hours"
    | "closed";
  market_data_quality: "provider" | "fallback";
  entry_price: number | null;
  stop_loss: number | null;
  take_profit1: number | null;
  notes: string[];
}

export interface SignalSetupScorecardStat {
  setup_type:
    | "opening_range_breakout"
    | "vwap_reclaim"
    | "pullback_continuation"
    | "failed_breakout"
    | "no_trade";
  total: number;
  target_hits: number;
  stop_hits: number;
  exit_signals: number;
  open: number;
  no_resolution: number;
  win_rate_pct: number;
}

export interface IntradayScorecardResponse {
  as_of: string;
  session_date: string;
  lookback_days: number;
  symbols_with_snapshots: number;
  actionable_signals: number;
  alerts_fired: number;
  fallback_alerts: number;
  items: SignalScorecardItem[];
  setup_stats: SignalSetupScorecardStat[];
}

export interface SignalsResponse {
  as_of: string;
  source: string;
  market_data_source: string;
  market_data_quality: "provider" | "fallback" | "mixed";
  market_clock: MarketClock;
  regime_headline: string;
  portfolio: SignalPortfolioState;
  focus: SignalFocus;
  alerts: SignalAlert[];
  items: TradingSignalRecord[];
}
