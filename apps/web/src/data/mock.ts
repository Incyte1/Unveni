export type StrategyType =
  | "Call Vertical"
  | "Put Spread"
  | "Calendar"
  | "Iron Condor"
  | "Call Fly";

export interface ScenarioRow {
  move: string;
  pnl: [number, number, number];
}

export interface Opportunity {
  id: string;
  symbol: string;
  structure: StrategyType;
  thesis: string;
  dte: number;
  dteBucket: string;
  score: number;
  expectedReturn: number;
  expectedShortfall: number;
  winRate: number;
  maxLoss: number;
  spreadBps: number;
  ivRank: number;
  delta: number;
  gamma: number;
  vega: number;
  theta: number;
  catalysts: string[];
  topDrivers: string[];
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
  label: string;
  value: number;
}

export interface BacktestSeries {
  equity: number[];
  drawdown: number[];
  calibration: number[];
  labels: string[];
  metrics: Array<{ label: string; value: string }>;
}

export const strategyFilters: Array<StrategyType | "All"> = [
  "All",
  "Call Vertical",
  "Put Spread",
  "Calendar",
  "Iron Condor",
  "Call Fly"
];

export const opportunities: Opportunity[] = [
  {
    id: "nvda-call-vertical-28d",
    symbol: "NVDA",
    structure: "Call Vertical",
    thesis:
      "AI infrastructure momentum is still intact, but the surface is rich enough that capped upside prices cleaner than naked premium.",
    dte: 28,
    dteBucket: "22-35 DTE",
    score: 94,
    expectedReturn: 17.4,
    expectedShortfall: -5.8,
    winRate: 63,
    maxLoss: 4.15,
    spreadBps: 48,
    ivRank: 71,
    delta: 0.34,
    gamma: 0.11,
    vega: 0.18,
    theta: -0.07,
    catalysts: ["Jobs in 2d", "NVDA supplier checks", "Semis breadth"],
    topDrivers: [
      "1m skew flattening",
      "Positive FinBERT cluster",
      "Macro beta supported by softer yields"
    ],
    payoff: [-1, -0.8, -0.3, 0.2, 0.8, 1.4, 1.8, 2, 2],
    scenario: [
      { move: "-3%", pnl: [-1.8, -1.4, -1.1] },
      { move: "0%", pnl: [-0.5, 0.2, 0.6] },
      { move: "+3%", pnl: [0.8, 1.6, 2] }
    ],
    notes: [
      "Use defined risk while IV remains above 70th percentile.",
      "Reduce size by half if 1D realized vol closes above 4.5%."
    ]
  },
  {
    id: "spy-calendar-35d",
    symbol: "SPY",
    structure: "Calendar",
    thesis:
      "Front-week event premium is elevated into CPI while the second month still screens under the realized-vol regime model.",
    dte: 35,
    dteBucket: "29-42 DTE",
    score: 88,
    expectedReturn: 11.2,
    expectedShortfall: -3.9,
    winRate: 58,
    maxLoss: 2.48,
    spreadBps: 29,
    ivRank: 63,
    delta: 0.06,
    gamma: 0.05,
    vega: 0.27,
    theta: 0.03,
    catalysts: ["CPI in 5d", "2Y yield regime", "Dealer gamma neutral"],
    topDrivers: [
      "Term structure inversion",
      "Event proximity feature",
      "Lower slippage than earnings-linked names"
    ],
    payoff: [-0.9, -0.6, -0.2, 0.1, 0.5, 0.9, 1.1, 0.8, 0.2],
    scenario: [
      { move: "-2%", pnl: [-1.2, -0.8, -0.2] },
      { move: "0%", pnl: [-0.3, 0.6, 1.1] },
      { move: "+2%", pnl: [-0.1, 0.5, 0.9] }
    ],
    notes: [
      "Vega-led setup; de-prioritize if front vol collapses before event.",
      "Good candidate for the low-delta sleeve."
    ]
  },
  {
    id: "aapl-put-spread-21d",
    symbol: "AAPL",
    structure: "Put Spread",
    thesis:
      "Momentum breadth is weakening and the ranker prefers cheaper downside protection over outright short gamma.",
    dte: 21,
    dteBucket: "15-28 DTE",
    score: 84,
    expectedReturn: 13.1,
    expectedShortfall: -4.6,
    winRate: 54,
    maxLoss: 3.05,
    spreadBps: 36,
    ivRank: 52,
    delta: -0.29,
    gamma: 0.08,
    vega: 0.12,
    theta: -0.05,
    catalysts: ["Consumer data softening", "Mega-cap breadth", "QQQ divergence"],
    topDrivers: [
      "Negative relative strength",
      "Skew bid versus 20-day baseline",
      "Risk-off macro composite"
    ],
    payoff: [-0.7, -0.4, 0.1, 0.6, 1.1, 1.5, 1.8, 1.8, 1.8],
    scenario: [
      { move: "-3%", pnl: [0.7, 1.2, 1.8] },
      { move: "0%", pnl: [-0.6, -0.2, 0.1] },
      { move: "+3%", pnl: [-1.1, -0.8, -0.5] }
    ],
    notes: [
      "Pairs well against long beta expressions elsewhere.",
      "Avoid adding if portfolio delta is already net short."
    ]
  },
  {
    id: "iwm-iron-condor-17d",
    symbol: "IWM",
    structure: "Iron Condor",
    thesis:
      "Small caps remain range-bound and the surface shape supports premium harvesting with hard ES caps.",
    dte: 17,
    dteBucket: "8-21 DTE",
    score: 79,
    expectedReturn: 8.6,
    expectedShortfall: -2.7,
    winRate: 67,
    maxLoss: 1.92,
    spreadBps: 33,
    ivRank: 58,
    delta: 0.01,
    gamma: -0.06,
    vega: -0.11,
    theta: 0.08,
    catalysts: ["No major macro in window", "RV under IV", "Breadth stabilization"],
    topDrivers: [
      "Range compression",
      "Spread quality in ETF complex",
      "Low concentration impact"
    ],
    payoff: [0.4, 0.8, 1.1, 1.2, 1.2, 1.1, 0.8, 0.4, -0.6],
    scenario: [
      { move: "-2%", pnl: [-0.8, 0.1, 0.6] },
      { move: "0%", pnl: [0.6, 1.2, 1.2] },
      { move: "+2%", pnl: [0.5, 1.1, 0.2] }
    ],
    notes: [
      "Keep width narrow; the risk engine should reject oversized short-vol clusters.",
      "This is the only short-vega candidate in the current top decile."
    ]
  },
  {
    id: "xom-call-fly-24d",
    symbol: "XOM",
    structure: "Call Fly",
    thesis:
      "Energy trend is constructive, but realized moves are slowing enough that a fly captures drift without overpaying for far-wing premium.",
    dte: 24,
    dteBucket: "22-35 DTE",
    score: 76,
    expectedReturn: 9.4,
    expectedShortfall: -2.9,
    winRate: 51,
    maxLoss: 1.61,
    spreadBps: 42,
    ivRank: 49,
    delta: 0.12,
    gamma: 0.04,
    vega: -0.03,
    theta: -0.01,
    catalysts: ["Crude trend", "OPEC headlines", "Energy factor leadership"],
    topDrivers: [
      "Tighter realized-vol band",
      "Sector relative momentum",
      "Low margin footprint"
    ],
    payoff: [-0.4, -0.1, 0.4, 0.9, 1.3, 1.1, 0.6, 0.1, -0.3],
    scenario: [
      { move: "-2%", pnl: [-0.7, -0.3, 0.1] },
      { move: "0%", pnl: [0.2, 0.8, 1.3] },
      { move: "+2%", pnl: [0.5, 1.1, 0.4] }
    ],
    notes: [
      "Smaller liquidity bucket; keep sizing subordinate to ETF structures.",
      "Useful example of a payoff-focused candidate in the ranking layer."
    ]
  }
];

export const riskMetrics: RiskMetric[] = [
  { label: "Portfolio delta", current: 0.23, limit: 0.45, unit: "" },
  { label: "Portfolio gamma", current: 0.12, limit: 0.2, unit: "" },
  { label: "Portfolio vega", current: 0.29, limit: 0.35, unit: "" },
  { label: "1D expected shortfall", current: 0.021, limit: 0.03, unit: "" }
];

export const exposureBuckets: ExposureBucket[] = [
  { label: "0-7 DTE", value: 6 },
  { label: "8-21 DTE", value: 18 },
  { label: "22-35 DTE", value: 42 },
  { label: "36-60 DTE", value: 34 }
];

export const backtest: BacktestSeries = {
  labels: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug"],
  equity: [1, 1.03, 1.02, 1.07, 1.11, 1.09, 1.15, 1.18],
  drawdown: [0, 0.01, 0.03, 0.01, 0, 0.02, 0.01, 0],
  calibration: [0.11, 0.27, 0.48, 0.71, 0.87],
  metrics: [
    { label: "CAGR", value: "18.4%" },
    { label: "Deflated Sharpe", value: "1.27" },
    { label: "PBO", value: "6.2%" },
    { label: "Avg spread paid", value: "34 bps" }
  ]
};

