from __future__ import annotations

from pipeline.config import BacktestConfig


def backtest_plan(config: BacktestConfig) -> dict[str, object]:
    return {
        "execution": {
            "entry_rule": config.entry_rule,
            "exit_rule": config.exit_rule
        },
        "limits": {
            "max_portfolio_delta": config.max_portfolio_delta,
            "max_portfolio_vega": config.max_portfolio_vega,
            "max_expected_shortfall": config.max_expected_shortfall
        },
        "reports": [
            "equity_curve",
            "drawdown",
            "calibration",
            "greeks_utilization"
        ]
    }

