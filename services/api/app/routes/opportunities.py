from fastapi import APIRouter, HTTPException

from app.models import OpportunitiesResponse, TradeDetail
from app.services.opportunities import (
    get_trade_detail as get_trade_detail_service,
    list_opportunities as list_opportunities_service
)

router = APIRouter(tags=["opportunities"])


@router.get("/opportunities", response_model=OpportunitiesResponse)
def list_opportunities() -> OpportunitiesResponse:
    return list_opportunities_service()


@router.get("/opportunities/{trade_id}", response_model=TradeDetail)
def get_trade_detail(trade_id: str) -> TradeDetail:
    trade = get_trade_detail_service(trade_id)
    if trade is None:
        raise HTTPException(status_code=404, detail="trade_not_found")
    return trade
