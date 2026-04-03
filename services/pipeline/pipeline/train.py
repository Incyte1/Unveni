from __future__ import annotations

from pipeline.config import TrainingConfig


def training_plan(config: TrainingConfig) -> dict[str, object]:
    return {
        "baseline_model": {
            "family": "gradient_boosted_tree",
            "objective": "trade_return_regression"
        },
        "rank_model": {
            "family": "lightgbm",
            "objective": config.rank_objective,
            "grouping_key": "trade_date"
        },
        "validation": config.validation_scheme,
        "governance_metrics": list(config.governance_metrics)
    }

