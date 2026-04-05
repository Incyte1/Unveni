from fastapi import APIRouter, Depends, status

from app.db import DatabaseSession, get_db_session
from app.models import (
    PaperOrderPlacementResponse,
    PaperOrderRequest,
    PaperOrdersResponse,
    PaperPortfolioSummary,
    PaperPositionsResponse
)
from app.services.paper_trading import get_portfolio_summary, list_open_positions, list_order_history, place_paper_order
from app.services.session import AuthenticatedSessionContext, require_authenticated_session

router = APIRouter(prefix="/paper", tags=["paper-trading"])


@router.get("/positions", response_model=PaperPositionsResponse)
def paper_positions(
    current_session: AuthenticatedSessionContext = Depends(require_authenticated_session),
    session: DatabaseSession = Depends(get_db_session)
) -> PaperPositionsResponse:
    return list_open_positions(session, current_session)


@router.get("/orders", response_model=PaperOrdersResponse)
def paper_orders(
    current_session: AuthenticatedSessionContext = Depends(require_authenticated_session),
    session: DatabaseSession = Depends(get_db_session)
) -> PaperOrdersResponse:
    return list_order_history(session, current_session)


@router.get("/summary", response_model=PaperPortfolioSummary)
def paper_summary(
    current_session: AuthenticatedSessionContext = Depends(require_authenticated_session),
    session: DatabaseSession = Depends(get_db_session)
) -> PaperPortfolioSummary:
    return get_portfolio_summary(session, current_session)


@router.post("/orders", response_model=PaperOrderPlacementResponse, status_code=status.HTTP_201_CREATED)
def submit_paper_order(
    payload: PaperOrderRequest,
    current_session: AuthenticatedSessionContext = Depends(require_authenticated_session),
    session: DatabaseSession = Depends(get_db_session)
) -> PaperOrderPlacementResponse:
    return place_paper_order(session, current_session, payload)
