from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class CandidateBuildConfig:
    horizon_days: int = 10
    min_open_interest: int = 500
    max_spread_bps: int = 60
    dte_buckets: tuple[tuple[int, int], ...] = ((8, 21), (22, 35), (36, 60))
    strategies: tuple[str, ...] = (
        "call_vertical",
        "put_spread",
        "calendar",
        "iron_condor"
    )


@dataclass(frozen=True)
class TrainingConfig:
    rank_objective: str = "lambdarank"
    regression_objective: str = "expected_shortfall_aware_return"
    validation_scheme: str = "walk_forward_with_embargo"
    governance_metrics: tuple[str, ...] = (
        "sharpe",
        "deflated_sharpe",
        "pbo",
        "expected_shortfall"
    )


@dataclass(frozen=True)
class BacktestConfig:
    entry_rule: str = "buy_at_ask_sell_at_bid"
    exit_rule: str = "profit_stop_time_barrier"
    max_portfolio_delta: float = 0.45
    max_portfolio_vega: float = 0.35
    max_expected_shortfall: float = 0.03


@dataclass(frozen=True)
class PipelineConfig:
    candidate_build: CandidateBuildConfig = field(default_factory=CandidateBuildConfig)
    training: TrainingConfig = field(default_factory=TrainingConfig)
    backtest: BacktestConfig = field(default_factory=BacktestConfig)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def default_config() -> PipelineConfig:
    return PipelineConfig()

