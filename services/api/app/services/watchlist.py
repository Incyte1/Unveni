from __future__ import annotations

import re
from datetime import datetime, timezone

from app.db import DatabaseSession
from app.errors import AppError
from app.models import (
    WatchlistDeleteResponse,
    WatchlistItemRecord,
    WatchlistItemUpsertRequest,
    WatchlistResponse
)
from app.repositories.watchlist import WatchlistRepository
from app.services.market import get_quote_snapshot
from app.services.session import AuthenticatedSessionContext


VALID_SYMBOL = re.compile(r"^[A-Z][A-Z0-9.\-]{0,15}$")


def _normalize_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if not normalized or not VALID_SYMBOL.fullmatch(normalized):
        raise AppError(
            code="invalid_symbol",
            message="Enter a valid symbol.",
            status_code=400
        )
    return normalized


def _normalize_notes(notes: str | None) -> str | None:
    if notes is None:
        return None
    normalized = notes.strip()
    return normalized or None


def _to_watchlist_item(item: dict[str, object]) -> WatchlistItemRecord:
    symbol = str(item["symbol"])
    return WatchlistItemRecord(
        symbol=symbol,
        notes=item["notes"] if item["notes"] else None,
        added_at=item["created_at"],
        updated_at=item["updated_at"],
        quote=get_quote_snapshot(symbol)
    )


def list_watchlist(
    session: DatabaseSession,
    current_session: AuthenticatedSessionContext
) -> WatchlistResponse:
    repository = WatchlistRepository(session)
    watchlist, items = repository.list_items(current_session.user_id)
    return WatchlistResponse(
        as_of=datetime.now(timezone.utc),
        watchlist_id=str(watchlist["id"]),
        items=[_to_watchlist_item(item) for item in items]
    )


def add_watchlist_item(
    session: DatabaseSession,
    current_session: AuthenticatedSessionContext,
    payload: WatchlistItemUpsertRequest
) -> WatchlistItemRecord:
    repository = WatchlistRepository(session)
    item = repository.upsert_item(
        current_session.user_id,
        _normalize_symbol(payload.symbol),
        _normalize_notes(payload.notes)
    )
    return _to_watchlist_item(dict(item))


def remove_watchlist_item(
    session: DatabaseSession,
    current_session: AuthenticatedSessionContext,
    symbol: str
) -> WatchlistDeleteResponse:
    normalized_symbol = _normalize_symbol(symbol)
    repository = WatchlistRepository(session)
    removed = repository.delete_item(current_session.user_id, normalized_symbol)
    return WatchlistDeleteResponse(removed=removed, symbol=normalized_symbol)
