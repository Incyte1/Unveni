from __future__ import annotations

from app.models import TradeExplanation
from app.sample_data import EXPLANATIONS


def get_trade_explanation(trade_id: str) -> TradeExplanation | None:
    return EXPLANATIONS.get(trade_id)
