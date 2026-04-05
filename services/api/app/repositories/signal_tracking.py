from __future__ import annotations

from collections.abc import Mapping

from app.db import DatabaseSession


class SignalTrackingRepository:
    def __init__(self, session: DatabaseSession) -> None:
        self.session = session

    def get_latest_snapshot(self, user_id: str, symbol: str) -> Mapping[str, object] | None:
        return self.session.fetchone(
            """
            SELECT *
            FROM signal_snapshots
            WHERE user_id = :user_id AND symbol = :symbol
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            {"user_id": user_id, "symbol": symbol}
        )

    def list_snapshots(
        self,
        user_id: str,
        symbol: str,
        limit: int = 20
    ) -> list[dict[str, object]]:
        return self.session.fetchall(
            """
            SELECT *
            FROM signal_snapshots
            WHERE user_id = :user_id AND symbol = :symbol
            ORDER BY created_at DESC, id DESC
            LIMIT :limit
            """,
            {"user_id": user_id, "symbol": symbol, "limit": limit}
        )

    def list_snapshots_in_window(
        self,
        user_id: str,
        created_after: str,
        created_before: str | None = None,
        limit: int = 500
    ) -> list[dict[str, object]]:
        params: dict[str, object] = {
            "user_id": user_id,
            "created_after": created_after,
            "limit": limit
        }
        where_clause = "user_id = :user_id AND created_at >= :created_after"
        if created_before is not None:
            params["created_before"] = created_before
            where_clause += " AND created_at <= :created_before"

        return self.session.fetchall(
            f"""
            SELECT *
            FROM signal_snapshots
            WHERE {where_clause}
            ORDER BY created_at DESC, id DESC
            LIMIT :limit
            """,
            params
        )

    def create_snapshot(self, row: Mapping[str, object]) -> None:
        self.session.execute(
            """
            INSERT INTO signal_snapshots (
                id,
                user_id,
                symbol,
                timeframe,
                setup_type,
                action,
                entry_state,
                confidence,
                score,
                thesis,
                entry_price,
                stop_loss,
                take_profit1,
                take_profit2,
                market_data_source,
                market_data_quality,
                is_actionable,
                has_position,
                market_phase,
                regime_headline,
                reasons_json,
                warnings_json,
                signal_fingerprint,
                transition_json,
                snapshot_json,
                created_at
            )
            VALUES (
                :id,
                :user_id,
                :symbol,
                :timeframe,
                :setup_type,
                :action,
                :entry_state,
                :confidence,
                :score,
                :thesis,
                :entry_price,
                :stop_loss,
                :take_profit1,
                :take_profit2,
                :market_data_source,
                :market_data_quality,
                :is_actionable,
                :has_position,
                :market_phase,
                :regime_headline,
                :reasons_json,
                :warnings_json,
                :signal_fingerprint,
                :transition_json,
                :snapshot_json,
                :created_at
            )
            """,
            row
        )

    def get_latest_alert_for_dedupe(
        self,
        user_id: str,
        dedupe_key: str,
        created_after: str
    ) -> Mapping[str, object] | None:
        return self.session.fetchone(
            """
            SELECT *
            FROM signal_alerts
            WHERE user_id = :user_id
              AND dedupe_key = :dedupe_key
              AND created_at >= :created_after
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            {
                "user_id": user_id,
                "dedupe_key": dedupe_key,
                "created_after": created_after
            }
        )

    def create_alert(self, row: Mapping[str, object]) -> None:
        self.session.execute(
            """
            INSERT INTO signal_alerts (
                id,
                user_id,
                symbol,
                snapshot_id,
                alert_type,
                severity,
                status,
                title,
                message,
                dedupe_key,
                change_types_json,
                data_quality,
                payload_json,
                created_at,
                read_at,
                acknowledged_at
            )
            VALUES (
                :id,
                :user_id,
                :symbol,
                :snapshot_id,
                :alert_type,
                :severity,
                :status,
                :title,
                :message,
                :dedupe_key,
                :change_types_json,
                :data_quality,
                :payload_json,
                :created_at,
                :read_at,
                :acknowledged_at
            )
            """,
            row
        )

    def list_alerts(
        self,
        user_id: str,
        *,
        limit: int = 25,
        created_after: str | None = None,
        status: str | None = None
    ) -> list[dict[str, object]]:
        params: dict[str, object] = {
            "user_id": user_id,
            "limit": limit
        }
        where_parts = ["user_id = :user_id"]
        if created_after is not None:
            params["created_after"] = created_after
            where_parts.append("created_at >= :created_after")
        if status is not None:
            params["status"] = status
            where_parts.append("status = :status")

        return self.session.fetchall(
            f"""
            SELECT *
            FROM signal_alerts
            WHERE {' AND '.join(where_parts)}
            ORDER BY created_at DESC, id DESC
            LIMIT :limit
            """,
            params
        )

    def get_alert(self, user_id: str, alert_id: str) -> Mapping[str, object] | None:
        return self.session.fetchone(
            """
            SELECT *
            FROM signal_alerts
            WHERE user_id = :user_id AND id = :alert_id
            LIMIT 1
            """,
            {"user_id": user_id, "alert_id": alert_id}
        )

    def update_alert_status(
        self,
        user_id: str,
        alert_id: str,
        *,
        status: str,
        read_at: str | None,
        acknowledged_at: str | None
    ) -> None:
        self.session.execute(
            """
            UPDATE signal_alerts
            SET
                status = :status,
                read_at = :read_at,
                acknowledged_at = :acknowledged_at
            WHERE user_id = :user_id AND id = :alert_id
            """,
            {
                "user_id": user_id,
                "alert_id": alert_id,
                "status": status,
                "read_at": read_at,
                "acknowledged_at": acknowledged_at
            }
        )
