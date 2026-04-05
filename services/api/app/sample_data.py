from __future__ import annotations

from datetime import datetime, timezone

from app.models import (
    ExplanationDriver,
    ExplanationWarning,
    Greeks,
    MarketBenchmark,
    MarketClock,
    MarketEvent,
    MarketOverviewResponse,
    MarketRegime,
    Opportunity,
    RiskSnapshot,
    ScenarioRow,
    TradeDetail,
    TradeExplanation
)


OPPORTUNITIES = [
    Opportunity(
        id="nvda-call-vertical-28d",
        symbol="NVDA",
        structure="Call Vertical",
        thesis=(
            "AI infrastructure momentum is intact, while capped upside trades better than"
            " naked premium under the current skew and macro mix."
        ),
        dte=28,
        score=94,
        expected_return=17.4,
        expected_shortfall=-5.8,
        win_rate=63,
        spread_bps=48,
        max_loss=4.15,
        catalysts=["Jobs in 2d", "Supplier checks", "Semis breadth"],
        top_drivers=[
            "1m skew flattening",
            "Positive FinBERT cluster",
            "Lower yields supporting beta"
        ],
        greeks=Greeks(delta=0.34, gamma=0.11, vega=0.18, theta=-0.07)
    ),
    Opportunity(
        id="spy-calendar-35d",
        symbol="SPY",
        structure="Calendar",
        thesis=(
            "Front-event premium into CPI remains elevated relative to the second month,"
            " which keeps the term-structure trade ranked near the top."
        ),
        dte=35,
        score=88,
        expected_return=11.2,
        expected_shortfall=-3.9,
        win_rate=58,
        spread_bps=29,
        max_loss=2.48,
        catalysts=["CPI in 5d", "Yield curve inflection", "Dealer gamma neutral"],
        top_drivers=[
            "Event proximity factor",
            "Vol term inversion",
            "Cleaner liquidity profile"
        ],
        greeks=Greeks(delta=0.06, gamma=0.05, vega=0.27, theta=0.03)
    ),
    Opportunity(
        id="aapl-put-spread-21d",
        symbol="AAPL",
        structure="Put Spread",
        thesis=(
            "The defensive sleeve prefers lower-cost downside convexity while breadth and"
            " macro composites soften."
        ),
        dte=21,
        score=84,
        expected_return=13.1,
        expected_shortfall=-4.6,
        win_rate=54,
        spread_bps=36,
        max_loss=3.05,
        catalysts=["QQQ divergence", "Consumer data softening", "Breadth decay"],
        top_drivers=[
            "Relative-strength rollover",
            "Skew bid versus baseline",
            "Portfolio hedge contribution"
        ],
        greeks=Greeks(delta=-0.29, gamma=0.08, vega=0.12, theta=-0.05)
    )
]

TRADE_DETAILS = {
    "nvda-call-vertical-28d": TradeDetail(
        id="nvda-call-vertical-28d",
        symbol="NVDA",
        structure="Call Vertical",
        thesis=OPPORTUNITIES[0].thesis,
        score=94,
        dte=28,
        iv_rank=71,
        spread_bps=48,
        expected_return=17.4,
        max_loss=4.15,
        expected_shortfall=-5.8,
        greeks=Greeks(delta=0.34, gamma=0.11, vega=0.18, theta=-0.07),
        payoff=[-1.0, -0.8, -0.3, 0.2, 0.8, 1.4, 1.8, 2.0, 2.0],
        scenario=[
            ScenarioRow(move="-3%", pnl=(-1.8, -1.4, -1.1)),
            ScenarioRow(move="0%", pnl=(-0.5, 0.2, 0.6)),
            ScenarioRow(move="+3%", pnl=(0.8, 1.6, 2.0))
        ],
        notes=[
            "Reject if slippage doubles versus the rolling 20-day median.",
            "Size down when portfolio vega exceeds 80% of limit."
        ]
    ),
    "spy-calendar-35d": TradeDetail(
        id="spy-calendar-35d",
        symbol="SPY",
        structure="Calendar",
        thesis=OPPORTUNITIES[1].thesis,
        score=88,
        dte=35,
        iv_rank=63,
        spread_bps=29,
        expected_return=11.2,
        max_loss=2.48,
        expected_shortfall=-3.9,
        greeks=Greeks(delta=0.06, gamma=0.05, vega=0.27, theta=0.03),
        payoff=[-0.9, -0.6, -0.2, 0.1, 0.5, 0.9, 1.1, 0.8, 0.2],
        scenario=[
            ScenarioRow(move="-2%", pnl=(-1.2, -0.8, -0.2)),
            ScenarioRow(move="0%", pnl=(-0.3, 0.6, 1.1)),
            ScenarioRow(move="+2%", pnl=(-0.1, 0.5, 0.9))
        ],
        notes=[
            "Prefer the setup while front-month event premium remains elevated.",
            "Keep sizing low if the portfolio is already long vega."
        ]
    ),
    "aapl-put-spread-21d": TradeDetail(
        id="aapl-put-spread-21d",
        symbol="AAPL",
        structure="Put Spread",
        thesis=OPPORTUNITIES[2].thesis,
        score=84,
        dte=21,
        iv_rank=52,
        spread_bps=36,
        expected_return=13.1,
        max_loss=3.05,
        expected_shortfall=-4.6,
        greeks=Greeks(delta=-0.29, gamma=0.08, vega=0.12, theta=-0.05),
        payoff=[-0.7, -0.4, 0.1, 0.6, 1.1, 1.5, 1.8, 1.8, 1.8],
        scenario=[
            ScenarioRow(move="-3%", pnl=(0.7, 1.2, 1.8)),
            ScenarioRow(move="0%", pnl=(-0.6, -0.2, 0.1)),
            ScenarioRow(move="+3%", pnl=(-1.1, -0.8, -0.5))
        ],
        notes=[
            "Use as a hedge sleeve, not a dominant directional view.",
            "Avoid adding when portfolio delta is already net short."
        ]
    )
}

RISK = RiskSnapshot(
    execution_mode="paper",
    entitlement="delayed-demo",
    metrics=[
        {"label": "Portfolio delta", "current": 0.23, "limit": 0.45, "unit": ""},
        {"label": "Portfolio gamma", "current": 0.12, "limit": 0.2, "unit": ""},
        {"label": "Portfolio vega", "current": 0.29, "limit": 0.35, "unit": ""},
        {"label": "1D expected shortfall", "current": 0.021, "limit": 0.03, "unit": ""}
    ],
    concentration=[
        {"bucket": "0-7 DTE", "value": 6},
        {"bucket": "8-21 DTE", "value": 18},
        {"bucket": "22-35 DTE", "value": 42},
        {"bucket": "36-60 DTE", "value": 34}
    ]
)

MARKET_OVERVIEW = MarketOverviewResponse(
    as_of=datetime.now(timezone.utc),
    source="render-api",
    quality="fallback",
    clock=MarketClock(
        is_open=True,
        session="regular",
        phase="midday",
        as_of=datetime.now(timezone.utc),
        next_open=None,
        next_close="2026-04-04T16:00:00-05:00",
        minutes_since_open=150,
        minutes_to_close=90,
        source="sample-data",
        quality="fallback"
    ),
    regime=MarketRegime(
        headline="Constructive risk with event-sensitive volatility",
        summary=(
            "Large-cap leadership remains intact, but front-end implied volatility is"
            " still elevated around macro releases."
        ),
        volatility_regime="Front-month event premium elevated",
        breadth_regime="Mega-cap leadership, small-cap range"
    ),
    benchmarks=[
        MarketBenchmark(
            symbol="SPY",
            move_pct=0.6,
            note="Index breadth stable with CPI event premium still elevated."
        ),
        MarketBenchmark(
            symbol="QQQ",
            move_pct=0.9,
            note="Semiconductor leadership continues to support growth beta."
        ),
        MarketBenchmark(
            symbol="IWM",
            move_pct=-0.1,
            note="Small caps remain range-bound with lower realized volatility."
        )
    ],
    highlights=[
        "Short-dated index volatility remains rich versus the next monthly tenor.",
        "Risk gates currently leave room for additional long-vega exposure but not oversized single-name concentration.",
        "Macro calendar density remains the main driver of intraday spread expansion."
    ],
    upcoming_events=[
        MarketEvent(label="CPI", scheduled_at="2026-04-05 08:30 ET", impact="high"),
        MarketEvent(label="Jobs", scheduled_at="2026-04-07 08:30 ET", impact="high"),
        MarketEvent(label="FOMC minutes", scheduled_at="2026-04-09 13:00 ET", impact="medium")
    ]
)

EXPLANATIONS = {
    "nvda-call-vertical-28d": TradeExplanation(
        trade_id="nvda-call-vertical-28d",
        headline="Defined-risk upside remains the cleanest expression for NVDA.",
        summary=(
            "The ranker prefers capped upside because directional momentum is still positive,"
            " while the current surface lets the short call subsidize entry without breaking the thesis."
        ),
        drivers=[
            ExplanationDriver(
                title="Skew flattening",
                detail="Upside call wing pricing improved enough to make the vertical materially cheaper than outright premium."
            ),
            ExplanationDriver(
                title="News and macro support",
                detail="Positive news clustering and softer yields continue to support growth-beta expressions."
            ),
            ExplanationDriver(
                title="Risk-budget fit",
                detail="Defined max loss keeps the trade inside current portfolio expected shortfall and vega limits."
            )
        ],
        warnings=[
            ExplanationWarning(
                severity="caution",
                title="Macro event risk",
                detail="Jobs data in two days can widen spreads and increase gap risk."
            ),
            ExplanationWarning(
                severity="risk",
                title="Concentration",
                detail="Do not oversize if the portfolio is already concentrated in semiconductor beta."
            )
        ]
    ),
    "spy-calendar-35d": TradeExplanation(
        trade_id="spy-calendar-35d",
        headline="The calendar targets front-month event premium rather than outright direction.",
        summary=(
            "The structure ranks well because the front expiry remains expensive into CPI,"
            " while the back month still screens as comparatively fair."
        ),
        drivers=[
            ExplanationDriver(
                title="Term-structure dislocation",
                detail="Front-month volatility is elevated relative to the next cycle, which improves calendar carry."
            ),
            ExplanationDriver(
                title="Low-delta positioning",
                detail="This setup adds vega without materially increasing directional exposure."
            )
        ],
        warnings=[
            ExplanationWarning(
                severity="caution",
                title="Vol crush timing",
                detail="If front-month volatility resets early, the structure loses much of its edge."
            )
        ]
    ),
    "aapl-put-spread-21d": TradeExplanation(
        trade_id="aapl-put-spread-21d",
        headline="The put spread is a lower-cost defensive expression.",
        summary=(
            "The ranking layer favors a defined-risk downside hedge because momentum breadth is softening,"
            " but outright short-gamma exposure is still expensive."
        ),
        drivers=[
            ExplanationDriver(
                title="Breadth deterioration",
                detail="Relative-strength signals and macro composites both lean defensive."
            ),
            ExplanationDriver(
                title="Hedge efficiency",
                detail="The spread preserves downside convexity while reducing premium outlay versus a naked put."
            )
        ],
        warnings=[
            ExplanationWarning(
                severity="info",
                title="Portfolio role",
                detail="This trade works best as a hedge sleeve rather than a primary directional short."
            )
        ]
    )
}

QUOTE_FIXTURES = {
    "AAPL": {"last": 192.18, "change": -1.14},
    "IWM": {"last": 205.44, "change": -0.31},
    "NVDA": {"last": 914.28, "change": 12.46},
    "QQQ": {"last": 448.51, "change": 4.08},
    "SPY": {"last": 521.37, "change": 3.15}
}


def opportunities_payload() -> dict[str, object]:
    return {
        "as_of": datetime.now(timezone.utc),
        "source": "render-api",
        "items": OPPORTUNITIES
    }


def market_overview_payload() -> dict[str, object]:
    return {
        "as_of": datetime.now(timezone.utc),
        "source": MARKET_OVERVIEW.source,
        "quality": MARKET_OVERVIEW.quality,
        "clock": MARKET_OVERVIEW.clock,
        "regime": MARKET_OVERVIEW.regime,
        "benchmarks": MARKET_OVERVIEW.benchmarks,
        "highlights": MARKET_OVERVIEW.highlights,
        "upcoming_events": MARKET_OVERVIEW.upcoming_events
    }
