from __future__ import annotations

from app.models import OpportunitiesResponse, TradeDetail
from app.sample_data import TRADE_DETAILS, opportunities_payload


def list_opportunities() -> OpportunitiesResponse:
    return OpportunitiesResponse.model_validate(opportunities_payload())


def get_trade_detail(trade_id: str) -> TradeDetail | None:
    return TRADE_DETAILS.get(trade_id)
