from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from uuid import uuid4

from app.db import DatabaseSession


DEFAULT_WATCHLIST_NAME = "default"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class WatchlistRepository:
    def __init__(self, session: DatabaseSession) -> None:
        self.session = session

    def ensure_default_watchlist(self, user_id: str) -> Mapping[str, object]:
        now = utc_now_iso()
        self.session.execute(
            """
            INSERT INTO watchlists (id, user_id, name, created_at, updated_at)
            VALUES (:id, :user_id, :name, :created_at, :updated_at)
            ON CONFLICT (user_id, name) DO NOTHING
            """,
            {
                "id": str(uuid4()),
                "user_id": user_id,
                "name": DEFAULT_WATCHLIST_NAME,
                "created_at": now,
                "updated_at": now
            }
        )
        watchlist = self.session.fetchone(
            """
            SELECT id, user_id, name, created_at, updated_at
            FROM watchlists
            WHERE user_id = :user_id AND name = :name
            """,
            {"user_id": user_id, "name": DEFAULT_WATCHLIST_NAME}
        )
        if watchlist is None:  # pragma: no cover - schema bootstrap guard
            raise RuntimeError("default watchlist could not be created")
        return watchlist

    def list_items(self, user_id: str) -> tuple[Mapping[str, object], list[dict[str, object]]]:
        watchlist = self.ensure_default_watchlist(user_id)
        items = self.session.fetchall(
            """
            SELECT id, symbol, notes, created_at, updated_at
            FROM watchlist_items
            WHERE watchlist_id = :watchlist_id
            ORDER BY created_at ASC, symbol ASC
            """,
            {"watchlist_id": watchlist["id"]}
        )
        return watchlist, items

    def upsert_item(self, user_id: str, symbol: str, notes: str | None) -> Mapping[str, object]:
        watchlist = self.ensure_default_watchlist(user_id)
        now = utc_now_iso()
        self.session.execute(
            """
            INSERT INTO watchlist_items (
                id,
                watchlist_id,
                symbol,
                notes,
                created_at,
                updated_at
            )
            VALUES (
                :id,
                :watchlist_id,
                :symbol,
                :notes,
                :created_at,
                :updated_at
            )
            ON CONFLICT (watchlist_id, symbol) DO UPDATE SET
                notes = excluded.notes,
                updated_at = excluded.updated_at
            """,
            {
                "id": str(uuid4()),
                "watchlist_id": watchlist["id"],
                "symbol": symbol,
                "notes": notes,
                "created_at": now,
                "updated_at": now
            }
        )
        item = self.session.fetchone(
            """
            SELECT id, symbol, notes, created_at, updated_at
            FROM watchlist_items
            WHERE watchlist_id = :watchlist_id AND symbol = :symbol
            """,
            {"watchlist_id": watchlist["id"], "symbol": symbol}
        )
        if item is None:  # pragma: no cover - upsert guard
            raise RuntimeError("watchlist item could not be persisted")
        return item

    def delete_item(self, user_id: str, symbol: str) -> bool:
        watchlist = self.ensure_default_watchlist(user_id)
        existing = self.session.fetchone(
            """
            SELECT id
            FROM watchlist_items
            WHERE watchlist_id = :watchlist_id AND symbol = :symbol
            """,
            {"watchlist_id": watchlist["id"], "symbol": symbol}
        )
        if existing is None:
            return False

        self.session.execute(
            """
            DELETE FROM watchlist_items
            WHERE watchlist_id = :watchlist_id AND symbol = :symbol
            """,
            {"watchlist_id": watchlist["id"], "symbol": symbol}
        )
        return True
