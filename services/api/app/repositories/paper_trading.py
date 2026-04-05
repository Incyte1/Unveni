from __future__ import annotations

from collections.abc import Mapping

from app.db import DatabaseSession


class PaperTradingRepository:
    def __init__(self, session: DatabaseSession) -> None:
        self.session = session

    def get_position(self, user_id: str, symbol: str) -> Mapping[str, object] | None:
        return self.session.fetchone(
            """
            SELECT user_id, symbol, quantity, average_cost, realized_pnl, created_at, updated_at
            FROM paper_positions
            WHERE user_id = :user_id AND symbol = :symbol
            """,
            {"user_id": user_id, "symbol": symbol}
        )

    def list_positions(self, user_id: str) -> list[dict[str, object]]:
        return self.session.fetchall(
            """
            SELECT user_id, symbol, quantity, average_cost, realized_pnl, created_at, updated_at
            FROM paper_positions
            WHERE user_id = :user_id
            ORDER BY symbol ASC
            """,
            {"user_id": user_id}
        )

    def list_orders(self, user_id: str) -> list[dict[str, object]]:
        return self.session.fetchall(
            """
            SELECT
                id,
                user_id,
                symbol,
                side,
                quantity,
                order_type,
                status,
                requested_price,
                fill_price,
                submitted_at,
                filled_at,
                rejection_reason
            FROM paper_orders
            WHERE user_id = :user_id
            ORDER BY submitted_at DESC, id DESC
            """,
            {"user_id": user_id}
        )

    def get_realized_pnl_total(self, user_id: str) -> float:
        row = self.session.fetchone(
            """
            SELECT COALESCE(SUM(realized_pnl), 0) AS realized_pnl
            FROM paper_fills
            WHERE user_id = :user_id
            """,
            {"user_id": user_id}
        )
        return float(row["realized_pnl"]) if row else 0.0

    def get_realized_pnl_since(self, user_id: str, filled_after: str) -> float:
        row = self.session.fetchone(
            """
            SELECT COALESCE(SUM(realized_pnl), 0) AS realized_pnl
            FROM paper_fills
            WHERE user_id = :user_id AND filled_at >= :filled_after
            """,
            {"user_id": user_id, "filled_after": filled_after}
        )
        return float(row["realized_pnl"]) if row else 0.0

    def record_rejected_order(self, order_row: Mapping[str, object]) -> None:
        self.session.execute(
            """
            INSERT INTO paper_orders (
                id,
                user_id,
                symbol,
                side,
                quantity,
                order_type,
                status,
                requested_price,
                fill_price,
                submitted_at,
                filled_at,
                rejection_reason
            )
            VALUES (
                :id,
                :user_id,
                :symbol,
                :side,
                :quantity,
                :order_type,
                :status,
                :requested_price,
                :fill_price,
                :submitted_at,
                :filled_at,
                :rejection_reason
            )
            """,
            order_row
        )

    def record_filled_order(
        self,
        order_row: Mapping[str, object],
        fill_row: Mapping[str, object],
        position_row: Mapping[str, object] | None
    ) -> None:
        self.session.execute(
            """
            INSERT INTO paper_orders (
                id,
                user_id,
                symbol,
                side,
                quantity,
                order_type,
                status,
                requested_price,
                fill_price,
                submitted_at,
                filled_at,
                rejection_reason
            )
            VALUES (
                :id,
                :user_id,
                :symbol,
                :side,
                :quantity,
                :order_type,
                :status,
                :requested_price,
                :fill_price,
                :submitted_at,
                :filled_at,
                :rejection_reason
            )
            """,
            order_row
        )
        self.session.execute(
            """
            INSERT INTO paper_fills (
                id,
                order_id,
                user_id,
                symbol,
                side,
                quantity,
                market_price,
                fill_price,
                realized_pnl,
                filled_at
            )
            VALUES (
                :id,
                :order_id,
                :user_id,
                :symbol,
                :side,
                :quantity,
                :market_price,
                :fill_price,
                :realized_pnl,
                :filled_at
            )
            """,
            fill_row
        )

        if position_row is None:
            self.session.execute(
                """
                DELETE FROM paper_positions
                WHERE user_id = :user_id AND symbol = :symbol
                """,
                {"user_id": order_row["user_id"], "symbol": order_row["symbol"]}
            )
            return

        self.session.execute(
            """
            INSERT INTO paper_positions (
                user_id,
                symbol,
                quantity,
                average_cost,
                realized_pnl,
                created_at,
                updated_at
            )
            VALUES (
                :user_id,
                :symbol,
                :quantity,
                :average_cost,
                :realized_pnl,
                :created_at,
                :updated_at
            )
            ON CONFLICT (user_id, symbol) DO UPDATE SET
                quantity = excluded.quantity,
                average_cost = excluded.average_cost,
                realized_pnl = excluded.realized_pnl,
                updated_at = excluded.updated_at
            """,
            position_row
        )
