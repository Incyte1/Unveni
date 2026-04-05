const opportunityItems = [
  {
    id: "nvda-call-vertical-28d",
    symbol: "NVDA",
    structure: "Call Vertical",
    thesis:
      "AI infrastructure momentum is intact, while capped upside trades better than naked premium under the current skew and macro mix.",
    dte: 28,
    score: 94,
    expected_return: 17.4,
    expected_shortfall: -5.8,
    win_rate: 63,
    spread_bps: 48,
    max_loss: 4.15,
    catalysts: ["Jobs in 2d", "Supplier checks", "Semis breadth"],
    top_drivers: [
      "1m skew flattening",
      "Positive FinBERT cluster",
      "Lower yields supporting beta"
    ],
    greeks: {
      delta: 0.34,
      gamma: 0.11,
      vega: 0.18,
      theta: -0.07
    }
  },
  {
    id: "spy-calendar-35d",
    symbol: "SPY",
    structure: "Calendar",
    thesis:
      "Front-event premium into CPI remains elevated relative to the second month, which keeps the term-structure trade ranked near the top.",
    dte: 35,
    score: 88,
    expected_return: 11.2,
    expected_shortfall: -3.9,
    win_rate: 58,
    spread_bps: 29,
    max_loss: 2.48,
    catalysts: ["CPI in 5d", "Yield curve inflection", "Dealer gamma neutral"],
    top_drivers: [
      "Event proximity factor",
      "Vol term inversion",
      "Cleaner liquidity profile"
    ],
    greeks: {
      delta: 0.06,
      gamma: 0.05,
      vega: 0.27,
      theta: 0.03
    }
  },
  {
    id: "aapl-put-spread-21d",
    symbol: "AAPL",
    structure: "Put Spread",
    thesis:
      "The defensive sleeve prefers lower-cost downside convexity while breadth and macro composites soften.",
    dte: 21,
    score: 84,
    expected_return: 13.1,
    expected_shortfall: -4.6,
    win_rate: 54,
    spread_bps: 36,
    max_loss: 3.05,
    catalysts: ["QQQ divergence", "Consumer data softening", "Breadth decay"],
    top_drivers: [
      "Relative-strength rollover",
      "Skew bid versus baseline",
      "Portfolio hedge contribution"
    ],
    greeks: {
      delta: -0.29,
      gamma: 0.08,
      vega: 0.12,
      theta: -0.05
    }
  }
] as const;

const tradeDetails = {
  "nvda-call-vertical-28d": {
    id: "nvda-call-vertical-28d",
    symbol: "NVDA",
    structure: "Call Vertical",
    thesis: opportunityItems[0].thesis,
    score: 94,
    dte: 28,
    iv_rank: 71,
    spread_bps: 48,
    expected_return: 17.4,
    max_loss: 4.15,
    expected_shortfall: -5.8,
    greeks: {
      delta: 0.34,
      gamma: 0.11,
      vega: 0.18,
      theta: -0.07
    },
    payoff: [-1, -0.8, -0.3, 0.2, 0.8, 1.4, 1.8, 2, 2],
    scenario: [
      { move: "-3%", pnl: [-1.8, -1.4, -1.1] },
      { move: "0%", pnl: [-0.5, 0.2, 0.6] },
      { move: "+3%", pnl: [0.8, 1.6, 2] }
    ],
    notes: [
      "Reject if slippage doubles versus the rolling 20-day median.",
      "Size down when portfolio vega exceeds 80% of limit."
    ]
  },
  "spy-calendar-35d": {
    id: "spy-calendar-35d",
    symbol: "SPY",
    structure: "Calendar",
    thesis: opportunityItems[1].thesis,
    score: 88,
    dte: 35,
    iv_rank: 63,
    spread_bps: 29,
    expected_return: 11.2,
    max_loss: 2.48,
    expected_shortfall: -3.9,
    greeks: {
      delta: 0.06,
      gamma: 0.05,
      vega: 0.27,
      theta: 0.03
    },
    payoff: [-0.9, -0.6, -0.2, 0.1, 0.5, 0.9, 1.1, 0.8, 0.2],
    scenario: [
      { move: "-2%", pnl: [-1.2, -0.8, -0.2] },
      { move: "0%", pnl: [-0.3, 0.6, 1.1] },
      { move: "+2%", pnl: [-0.1, 0.5, 0.9] }
    ],
    notes: [
      "Prefer the setup while front-month event premium remains elevated.",
      "Keep sizing low if the portfolio is already long vega."
    ]
  },
  "aapl-put-spread-21d": {
    id: "aapl-put-spread-21d",
    symbol: "AAPL",
    structure: "Put Spread",
    thesis: opportunityItems[2].thesis,
    score: 84,
    dte: 21,
    iv_rank: 52,
    spread_bps: 36,
    expected_return: 13.1,
    max_loss: 3.05,
    expected_shortfall: -4.6,
    greeks: {
      delta: -0.29,
      gamma: 0.08,
      vega: 0.12,
      theta: -0.05
    },
    payoff: [-0.7, -0.4, 0.1, 0.6, 1.1, 1.5, 1.8, 1.8, 1.8],
    scenario: [
      { move: "-3%", pnl: [0.7, 1.2, 1.8] },
      { move: "0%", pnl: [-0.6, -0.2, 0.1] },
      { move: "+3%", pnl: [-1.1, -0.8, -0.5] }
    ],
    notes: [
      "Use as a hedge sleeve, not a dominant directional view.",
      "Avoid adding when portfolio delta is already net short."
    ]
  }
} as const;

const explanations = {
  "nvda-call-vertical-28d": {
    trade_id: "nvda-call-vertical-28d",
    headline: "Defined-risk upside remains the cleanest expression for NVDA.",
    summary:
      "The ranker prefers capped upside because directional momentum is still positive, while the current surface lets the short call subsidize entry without breaking the thesis.",
    drivers: [
      {
        title: "Skew flattening",
        detail:
          "Upside call wing pricing improved enough to make the vertical materially cheaper than outright premium."
      },
      {
        title: "News and macro support",
        detail:
          "Positive news clustering and softer yields continue to support growth-beta expressions."
      },
      {
        title: "Risk-budget fit",
        detail:
          "Defined max loss keeps the trade inside current portfolio expected shortfall and vega limits."
      }
    ],
    warnings: [
      {
        severity: "caution",
        title: "Macro event risk",
        detail: "Jobs data in two days can widen spreads and increase gap risk."
      },
      {
        severity: "risk",
        title: "Concentration",
        detail:
          "Do not oversize if the portfolio is already concentrated in semiconductor beta."
      }
    ]
  },
  "spy-calendar-35d": {
    trade_id: "spy-calendar-35d",
    headline: "The calendar targets front-month event premium rather than outright direction.",
    summary:
      "The structure ranks well because the front expiry remains expensive into CPI, while the back month still screens as comparatively fair.",
    drivers: [
      {
        title: "Term-structure dislocation",
        detail:
          "Front-month volatility is elevated relative to the next cycle, which improves calendar carry."
      },
      {
        title: "Low-delta positioning",
        detail:
          "This setup adds vega without materially increasing directional exposure."
      }
    ],
    warnings: [
      {
        severity: "caution",
        title: "Vol crush timing",
        detail:
          "If front-month volatility resets early, the structure loses much of its edge."
      }
    ]
  },
  "aapl-put-spread-21d": {
    trade_id: "aapl-put-spread-21d",
    headline: "The put spread is a lower-cost defensive expression.",
    summary:
      "The ranking layer favors a defined-risk downside hedge because momentum breadth is softening, but outright short-gamma exposure is still expensive.",
    drivers: [
      {
        title: "Breadth deterioration",
        detail:
          "Relative-strength signals and macro composites both lean defensive."
      },
      {
        title: "Hedge efficiency",
        detail:
          "The spread preserves downside convexity while reducing premium outlay versus a naked put."
      }
    ],
    warnings: [
      {
        severity: "info",
        title: "Portfolio role",
        detail:
          "This trade works best as a hedge sleeve rather than a primary directional short."
      }
    ]
  }
} as const;

export function buildSessionFallback() {
  return {
    mode: "anonymous",
    is_authenticated: false,
    user: null,
    entitlement: "delayed-demo",
    execution_mode: "paper",
    session_strategy: "development",
    requires_local_token: false,
    expires_at: null
  };
}

export function buildOpportunitiesFallback() {
  return {
    as_of: new Date().toISOString(),
    source: "edge-fallback",
    items: opportunityItems
  };
}

export function buildTradeDetailFallback(tradeId: string) {
  return tradeDetails[tradeId as keyof typeof tradeDetails];
}

export function buildExplanationFallback(tradeId: string) {
  return explanations[tradeId as keyof typeof explanations];
}

export function buildRiskFallback() {
  return {
    execution_mode: "paper",
    entitlement: "delayed-demo",
    metrics: [
      { label: "Portfolio delta", current: 0.23, limit: 0.45, unit: "" },
      { label: "Portfolio gamma", current: 0.12, limit: 0.2, unit: "" },
      { label: "Portfolio vega", current: 0.29, limit: 0.35, unit: "" },
      { label: "1D expected shortfall", current: 0.021, limit: 0.03, unit: "" }
    ],
    concentration: [
      { bucket: "0-7 DTE", value: 6 },
      { bucket: "8-21 DTE", value: 18 },
      { bucket: "22-35 DTE", value: 42 },
      { bucket: "36-60 DTE", value: 34 }
    ]
  };
}

export function buildMarketOverviewFallback() {
  const now = new Date().toISOString();
  return {
    as_of: now,
    source: "edge-fallback",
    quality: "fallback",
    clock: {
      is_open: false,
      session: "closed",
      phase: "closed",
      as_of: now,
      next_open: "2026-04-06 09:30 ET",
      next_close: "2026-04-06 16:00 ET",
      minutes_since_open: null,
      minutes_to_close: null,
      source: "fallback-clock",
      quality: "fallback"
    },
    regime: {
      headline: "Premarket preparation only",
      summary:
        "Fallback mode keeps the dashboard usable, but the intraday engine should still wait for the regular session to form before treating anything as tradable.",
      volatility_regime: "Fallback intraday range is moderate, so stops stay tight by default.",
      breadth_regime: "Breadth is mixed and no benchmark is clearing a clean intraday trigger yet."
    },
    benchmarks: [
      {
        symbol: "SPY",
        move_pct: 0.2,
        note: "SPY is hovering around fallback VWAP and still inside the opening range."
      },
      {
        symbol: "QQQ",
        move_pct: 0.4,
        note: "QQQ is holding slightly above fallback VWAP, but follow-through is not broad yet."
      },
      {
        symbol: "IWM",
        move_pct: -0.3,
        note: "IWM is lagging and keeping breadth from becoming cleanly constructive."
      }
    ],
    highlights: [
      "Session phase is closed, so the engine is in planning mode rather than trade-now mode.",
      "Fallback intraday data is explicit and should not be mistaken for live provider data.",
      "No fresh day trade should be forced until opening range and VWAP conditions are clean."
    ],
    upcoming_events: [
      { label: "Next market open", scheduled_at: "2026-04-06 09:30 ET", impact: "medium" }
    ]
  };
}

export function buildSignalsFallback() {
  const now = new Date().toISOString();

  return {
    as_of: now,
    source: "edge-fallback",
    market_data_source: "fallback-market-data",
    market_data_quality: "fallback",
    market_clock: {
      is_open: false,
      session: "closed",
      phase: "closed",
      as_of: now,
      next_open: "2026-04-06 09:30 ET",
      next_close: "2026-04-06 16:00 ET",
      minutes_since_open: null,
      minutes_to_close: null,
      source: "fallback-clock",
      quality: "fallback"
    },
    regime_headline: "Premarket preparation only",
    portfolio: {
      capital_base: 100000,
      gross_exposure: 0,
      gross_exposure_pct: 0,
      available_exposure_pct: 40,
      max_total_exposure_pct: 40,
      max_risk_per_trade_pct: 0.4,
      max_daily_loss_pct: 1.5,
      max_open_positions: 4,
      max_symbol_concentration_pct: 18,
      open_positions: 0,
      risk_utilization_pct: 58,
      daily_pnl: 0,
      daily_pnl_pct: 0,
      daily_loss_limit_hit: false,
      flatten_before_close: false,
      warnings: []
    },
    focus: {
      headline: "Stand aside right now",
      summary:
        "Stand aside in NVDA because there is no clean intraday trade right now.",
      symbol: "NVDA",
      action: "NO_TRADE",
      next_steps: [
        "Wait for NVDA to either break the opening range cleanly, reclaim VWAP with follow-through, or build a cleaner pullback continuation before treating it as a live day trade.",
        "Do nothing until the trigger level and confirmation conditions are both clean."
      ],
      warnings: ["Fallback intraday data is explicit; do not confuse it with live provider data."]
    },
    alerts: [
      {
        id: "regime-change",
        type: "regime_change",
        symbol: null,
        severity: "caution",
        title: "Session phase matters right now",
        message: "Closed or premarket conditions are for planning, not forced entries.",
        timestamp: now,
        status: "new",
        snapshot_id: null,
        change_types: ["session_changed"],
        data_quality: "fallback",
        read_at: null,
        acknowledged_at: null
      }
    ],
    items: [
      {
        symbol: "NVDA",
        action: "NO_TRADE",
        confidence: 52,
        score: 58,
        setup_type: "opening_range_breakout",
        entry_state: "wait_for_confirmation",
        strategy_type: "Opening range breakout",
        timeframe: "5m execution / 15m confirmation",
        thesis:
          "Wait on NVDA; the opening range breakout setup is forming but price has not confirmed through the trigger yet.",
        trigger_price: 914.3,
        entry_price: 914.3,
        entry_zone: "$913.39 - $915.67",
        stop_loss: 902.1,
        take_profit1: null,
        take_profit2: null,
        invalidation: "Stand aside if NVDA loses the opening range low before breaking $914.30.",
        risk_reward: null,
        position_size_pct: 0,
        reasons: [
          "NVDA is sitting just under the opening range high at $913.39.",
          "Trend alignment is bullish and relative volume is 1.24x."
        ],
        warnings: [
          "Do not front-run the breakout while price is still inside the range."
        ],
        timestamp: now,
        is_actionable: false,
        has_position: false,
        market_data_source: "deterministic-1min-candles-1min-close",
        market_data_quality: "fallback",
        current_position: null,
        opportunity_id: null,
        next_watch:
          "Buy only after a clean push through $913.39 with volume holding above the recent 5-minute average.",
        entry_rules: [
          {
            label: "Opening range break",
            status: "watch",
            detail: "Trigger is $913.39."
          },
          {
            label: "Volume confirmation",
            status: "watch",
            detail: "Relative volume is 1.24x."
          },
          {
            label: "Risk budget",
            status: "met",
            detail: "Available exposure is 40.00%."
          }
        ],
        exit_rules: [
          {
            label: "Protective stop",
            status: "watch",
            detail: "No entry yet, so keep the setup on watch only."
          },
          {
            label: "Target 1",
            status: "watch",
            detail: "Targets become active only after the breakout confirms."
          },
          {
            label: "End-of-day flatten",
            status: "watch",
            detail: "Ignore the setup if the trigger only arrives too close to the close."
          }
        ],
        trailing_stop: null,
        intraday_features: {
          execution_interval: "5min",
          confirmation_interval: "15min",
          session_phase: "closed",
          opening_range_high: 913.39,
          opening_range_low: 902.1,
          session_high: 913.39,
          session_low: 899.8,
          vwap: 907.45,
          momentum_5m_pct: 0.32,
          momentum_15m_pct: 0.58,
          pullback_depth_pct: 0.41,
          relative_volume: 1.24,
          session_range_pct: 1.51,
          trend_alignment: "bullish",
          breakout_state: "inside_range",
          distance_to_stop_pct: null
        }
      },
      {
        symbol: "AAPL",
        action: "NO_TRADE",
        confidence: 48,
        score: 42,
        setup_type: "no_trade",
        entry_state: "stand_aside",
        strategy_type: "Stand aside",
        timeframe: "5m execution / 15m confirmation",
        thesis:
          "Stand aside in AAPL because there is no clean intraday trade right now.",
        trigger_price: null,
        entry_price: null,
        entry_zone: null,
        stop_loss: null,
        take_profit1: null,
        take_profit2: null,
        invalidation: "Do nothing unless AAPL starts trading through a cleaner intraday trigger.",
        risk_reward: null,
        position_size_pct: 0,
        reasons: [
          "AAPL does not currently have a clean intraday setup that clears the day-trading bar.",
          "Breakout state is inside range with trend alignment mixed."
        ],
        warnings: ["The engine is monitoring this symbol from the default universe, not because it is already on your watchlist."],
        timestamp: now,
        is_actionable: false,
        has_position: false,
        market_data_source: "deterministic-1min-candles-1min-close",
        market_data_quality: "fallback",
        current_position: null,
        opportunity_id: null,
        next_watch:
          "Wait for AAPL to either break the opening range cleanly, reclaim VWAP with follow-through, or build a cleaner pullback continuation before treating it as a live day trade.",
        entry_rules: [
          {
            label: "Session window",
            status: "blocked",
            detail: "Current phase is closed."
          },
          {
            label: "Trend alignment",
            status: "watch",
            detail: "Trend alignment is mixed and no clean intraday setup is active."
          },
          {
            label: "Risk budget",
            status: "watch",
            detail: "Available exposure is 40.00%."
          }
        ],
        exit_rules: [
          {
            label: "Protective stop",
            status: "watch",
            detail: "No active trade means no stop needs to be carried."
          },
          {
            label: "End-of-day flatten",
            status: "watch",
            detail: "Stay flat into the close unless a cleaner setup forms earlier."
          },
          {
            label: "Setup activation",
            status: "watch",
            detail: "Wait for a cleaner intraday trigger."
          }
        ],
        trailing_stop: null,
        intraday_features: {
          execution_interval: "5min",
          confirmation_interval: "15min",
          session_phase: "closed",
          opening_range_high: 192.6,
          opening_range_low: 190.7,
          session_high: 193.1,
          session_low: 190.2,
          vwap: 191.85,
          momentum_5m_pct: -0.08,
          momentum_15m_pct: 0.02,
          pullback_depth_pct: 0.27,
          relative_volume: 0.86,
          session_range_pct: 1.52,
          trend_alignment: "mixed",
          breakout_state: "inside_range",
          distance_to_stop_pct: null
        }
      }
    ]
  };
}

export function buildSignalAlertsFallback() {
  return {
    as_of: new Date().toISOString(),
    items: []
  };
}

export function buildSignalHistoryFallback(symbol: string) {
  return {
    as_of: new Date().toISOString(),
    symbol: symbol.toUpperCase(),
    items: []
  };
}

export function buildIntradayScorecardFallback() {
  return {
    as_of: new Date().toISOString(),
    session_date: new Date().toISOString().slice(0, 10),
    lookback_days: 1,
    symbols_with_snapshots: 0,
    actionable_signals: 0,
    alerts_fired: 0,
    fallback_alerts: 0,
    items: [],
    setup_stats: []
  };
}
