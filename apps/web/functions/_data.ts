export const opportunities = [
  {
    id: "nvda-call-vertical-28d",
    symbol: "NVDA",
    structure: "Call Vertical",
    score: 94,
    expectedReturn: 17.4,
    expectedShortfall: -5.8,
    winRate: 63,
    spreadBps: 48,
    dte: 28,
    catalysts: ["Jobs in 2d", "Semis breadth"]
  },
  {
    id: "spy-calendar-35d",
    symbol: "SPY",
    structure: "Calendar",
    score: 88,
    expectedReturn: 11.2,
    expectedShortfall: -3.9,
    winRate: 58,
    spreadBps: 29,
    dte: 35,
    catalysts: ["CPI in 5d", "Term structure"]
  },
  {
    id: "aapl-put-spread-21d",
    symbol: "AAPL",
    structure: "Put Spread",
    score: 84,
    expectedReturn: 13.1,
    expectedShortfall: -4.6,
    winRate: 54,
    spreadBps: 36,
    dte: 21,
    catalysts: ["QQQ divergence", "Risk-off macro"]
  }
];

export const tradeDetails = {
  "nvda-call-vertical-28d": {
    id: "nvda-call-vertical-28d",
    symbol: "NVDA",
    structure: "Call Vertical",
    score: 94,
    summary:
      "Defined-risk upside structure selected by the ranking layer after skew flattening and positive news clustering.",
    greeks: {
      delta: 0.34,
      gamma: 0.11,
      vega: 0.18,
      theta: -0.07
    },
    limits: {
      maxLoss: 4.15,
      expectedShortfall: -5.8
    }
  },
  "spy-calendar-35d": {
    id: "spy-calendar-35d",
    symbol: "SPY",
    structure: "Calendar",
    score: 88,
    summary:
      "Event-premium expression that isolates the front-month versus second-month volatility spread into CPI.",
    greeks: {
      delta: 0.06,
      gamma: 0.05,
      vega: 0.27,
      theta: 0.03
    },
    limits: {
      maxLoss: 2.48,
      expectedShortfall: -3.9
    }
  },
  "aapl-put-spread-21d": {
    id: "aapl-put-spread-21d",
    symbol: "AAPL",
    structure: "Put Spread",
    score: 84,
    summary:
      "Lower-cost downside hedge prioritized when momentum breadth and macro factors move toward the defensive regime cluster.",
    greeks: {
      delta: -0.29,
      gamma: 0.08,
      vega: 0.12,
      theta: -0.05
    },
    limits: {
      maxLoss: 3.05,
      expectedShortfall: -4.6
    }
  }
} as const;

export const risk = {
  executionMode: "paper",
  entitlement: "delayed-demo",
  metrics: [
    { label: "Portfolio delta", current: 0.23, limit: 0.45 },
    { label: "Portfolio vega", current: 0.29, limit: 0.35 },
    { label: "1D expected shortfall", current: 0.021, limit: 0.03 }
  ]
};

