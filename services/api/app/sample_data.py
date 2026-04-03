from __future__ import annotations

from datetime import datetime, timezone

from app.models import Greeks, Opportunity, RiskSnapshot, TradeDetail


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
    opportunity.id: TradeDetail(
        id=opportunity.id,
        symbol=opportunity.symbol,
        structure=opportunity.structure,
        thesis=opportunity.thesis,
        score=opportunity.score,
        max_loss=opportunity.max_loss,
        expected_shortfall=opportunity.expected_shortfall,
        greeks=opportunity.greeks,
        top_drivers=opportunity.top_drivers,
        notes=[
            "Reject if slippage doubles versus the rolling 20-day median.",
            "Size down when portfolio vega exceeds 80% of limit."
        ]
    )
    for opportunity in OPPORTUNITIES
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


def opportunities_payload() -> dict[str, object]:
    return {
        "as_of": datetime.now(timezone.utc),
        "source": "render-api",
        "items": OPPORTUNITIES
    }

