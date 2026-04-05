from fastapi import APIRouter, Depends

from app.models import RiskSnapshot, SessionResponse
from app.services.market import get_risk_snapshot
from app.services.session import request_session

router = APIRouter(tags=["risk"])


@router.get("/risk", response_model=RiskSnapshot)
def risk_snapshot(
    session: SessionResponse = Depends(request_session)
) -> RiskSnapshot:
    return get_risk_snapshot(session)
