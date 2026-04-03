from fastapi import APIRouter

from app.models import RiskSnapshot
from app.sample_data import RISK

router = APIRouter(tags=["risk"])


@router.get("/risk", response_model=RiskSnapshot)
def risk_snapshot() -> RiskSnapshot:
    return RISK

