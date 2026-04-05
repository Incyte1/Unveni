from fastapi import APIRouter, Depends, status

from app.db import DatabaseSession, get_db_session
from app.models import (
    WatchlistDeleteResponse,
    WatchlistItemRecord,
    WatchlistItemUpsertRequest,
    WatchlistResponse
)
from app.services.session import AuthenticatedSessionContext, require_authenticated_session
from app.services.watchlist import add_watchlist_item, list_watchlist, remove_watchlist_item

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


@router.get("", response_model=WatchlistResponse)
def watchlist_snapshot(
    current_session: AuthenticatedSessionContext = Depends(require_authenticated_session),
    session: DatabaseSession = Depends(get_db_session)
) -> WatchlistResponse:
    return list_watchlist(session, current_session)


@router.post("/items", response_model=WatchlistItemRecord, status_code=status.HTTP_201_CREATED)
def create_watchlist_item(
    payload: WatchlistItemUpsertRequest,
    current_session: AuthenticatedSessionContext = Depends(require_authenticated_session),
    session: DatabaseSession = Depends(get_db_session)
) -> WatchlistItemRecord:
    return add_watchlist_item(session, current_session, payload)


@router.delete("/items/{symbol}", response_model=WatchlistDeleteResponse)
def delete_watchlist_item(
    symbol: str,
    current_session: AuthenticatedSessionContext = Depends(require_authenticated_session),
    session: DatabaseSession = Depends(get_db_session)
) -> WatchlistDeleteResponse:
    return remove_watchlist_item(session, current_session, symbol)
