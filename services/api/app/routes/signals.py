from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.db import DatabaseSession, get_db_session
from app.models import (
    IntradayScorecardResponse,
    SessionResponse,
    SignalAlert,
    SignalAlertsResponse,
    SignalAlertStatus,
    SignalAlertStatusUpdateRequest,
    SignalHistoryResponse,
    SignalsResponse
)
from app.services.session import (
    AuthenticatedSessionContext,
    optional_authenticated_session,
    require_authenticated_session,
    request_session
)
from app.services.signals import get_signals
from app.services.signal_tracking import (
    get_intraday_scorecard,
    get_signal_history,
    list_signal_alerts,
    update_signal_alert_status
)


router = APIRouter(tags=["signals"])


@router.get("/signals/alerts", response_model=SignalAlertsResponse)
def signal_alerts(
    limit: int = Query(default=25, ge=1, le=100),
    minutes: int | None = Query(default=None, ge=1, le=240),
    status: SignalAlertStatus | None = Query(default=None),
    current_session: AuthenticatedSessionContext = Depends(require_authenticated_session),
    session: DatabaseSession = Depends(get_db_session)
) -> SignalAlertsResponse:
    return list_signal_alerts(
        session,
        current_session,
        limit=limit,
        minutes=minutes,
        status=status
    )


@router.get("/signals/alerts/history", response_model=SignalAlertsResponse)
def signal_alert_history(
    limit: int = Query(default=100, ge=1, le=100),
    status: SignalAlertStatus | None = Query(default=None),
    current_session: AuthenticatedSessionContext = Depends(require_authenticated_session),
    session: DatabaseSession = Depends(get_db_session)
) -> SignalAlertsResponse:
    return list_signal_alerts(
        session,
        current_session,
        limit=limit,
        status=status
    )


@router.patch("/signals/alerts/{alert_id}", response_model=SignalAlert)
def patch_signal_alert(
    alert_id: str,
    payload: SignalAlertStatusUpdateRequest,
    current_session: AuthenticatedSessionContext = Depends(require_authenticated_session),
    session: DatabaseSession = Depends(get_db_session)
) -> SignalAlert:
    return update_signal_alert_status(
        session,
        current_session,
        alert_id,
        status=payload.status
    )


@router.get("/signals/history/{symbol}", response_model=SignalHistoryResponse)
def signal_history(
    symbol: str,
    limit: int = Query(default=20, ge=1, le=30),
    current_session: AuthenticatedSessionContext = Depends(require_authenticated_session),
    session: DatabaseSession = Depends(get_db_session)
) -> SignalHistoryResponse:
    return get_signal_history(
        session,
        current_session,
        symbol,
        limit=limit
    )


@router.get("/signals/scorecard", response_model=IntradayScorecardResponse)
def signal_scorecard(
    lookback_days: int = Query(default=1, ge=1, le=5),
    current_session: AuthenticatedSessionContext = Depends(require_authenticated_session),
    session: DatabaseSession = Depends(get_db_session)
) -> IntradayScorecardResponse:
    return get_intraday_scorecard(
        session,
        current_session,
        lookback_days=lookback_days
    )


@router.get("/signals", response_model=SignalsResponse)
def signal_snapshot(
    session_state: SessionResponse = Depends(request_session),
    current_session: AuthenticatedSessionContext | None = Depends(optional_authenticated_session),
    session: DatabaseSession = Depends(get_db_session)
) -> SignalsResponse:
    return get_signals(session, session_state, current_session)
