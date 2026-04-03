from fastapi import APIRouter, HTTPException

from app.models import OpportunitiesResponse, TradeDetail
from app.sample_data import TRADE_DETAILS, opportunities_payload

router = APIRouter(tags=["opportunities"])


@router.get("/opportunities", response_model=OpportunitiesResponse)
def list_opportunities() -> OpportunitiesResponse:
    return OpportunitiesResponse.model_validate(opportunities_payload())


@router.get("/opportunities/{trade_id}", response_model=TradeDetail)
def get_trade_detail(trade_id: str) -> TradeDetail:
    trade = TRADE_DETAILS.get(trade_id)
    if trade is None:
        raise HTTPException(status_code=404, detail="trade_not_found")
    return trade

