from fastapi import APIRouter, HTTPException

from app.models import TradeExplanation
from app.services.explanations import get_trade_explanation

router = APIRouter(tags=["explanations"])


@router.get("/explanations/{trade_id}", response_model=TradeExplanation)
def trade_explanation(trade_id: str) -> TradeExplanation:
    explanation = get_trade_explanation(trade_id)
    if explanation is None:
        raise HTTPException(status_code=404, detail="trade_not_found")
    return explanation
