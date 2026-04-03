from __future__ import annotations

from dataclasses import asdict, dataclass

from pipeline.config import CandidateBuildConfig


@dataclass(frozen=True)
class CandidateTrade:
    trade_id: str
    symbol: str
    strategy: str
    dte: int
    expected_return: float
    expected_shortfall: float
    spread_bps: int
    feature_flags: tuple[str, ...]


def build_candidate_set(config: CandidateBuildConfig) -> dict[str, object]:
    candidates = [
        CandidateTrade(
            trade_id="nvda-call-vertical-28d",
            symbol="NVDA",
            strategy="call_vertical",
            dte=28,
            expected_return=17.4,
            expected_shortfall=-5.8,
            spread_bps=48,
            feature_flags=("skew_flattening", "positive_finbert", "yield_relief")
        ),
        CandidateTrade(
            trade_id="spy-calendar-35d",
            symbol="SPY",
            strategy="calendar",
            dte=35,
            expected_return=11.2,
            expected_shortfall=-3.9,
            spread_bps=29,
            feature_flags=("event_proximity", "term_structure", "vega_positive")
        ),
        CandidateTrade(
            trade_id="aapl-put-spread-21d",
            symbol="AAPL",
            strategy="put_spread",
            dte=21,
            expected_return=13.1,
            expected_shortfall=-4.6,
            spread_bps=36,
            feature_flags=("negative_relative_strength", "risk_off_macro", "hedge_value")
        )
    ]
    return {
        "config": {
            "horizon_days": config.horizon_days,
            "max_spread_bps": config.max_spread_bps,
            "strategies": list(config.strategies)
        },
        "candidates": [asdict(candidate) for candidate in candidates]
    }

