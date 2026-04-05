from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime, timezone

from app.config import settings
from app.db import Database, DatabaseSession, database
from app.errors import MigrationError


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Migration:
    identifier: str
    description: str
    statements: tuple[str, ...]


MIGRATIONS: tuple[Migration, ...] = (
    Migration(
        identifier="0001_phase2_persistence",
        description="watchlists and paper trading persistence",
        statements=(
            """
            CREATE TABLE IF NOT EXISTS watchlists (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                UNIQUE (user_id, name)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS watchlist_items (
                id TEXT PRIMARY KEY,
                watchlist_id TEXT NOT NULL REFERENCES watchlists(id) ON DELETE CASCADE,
                symbol TEXT NOT NULL,
                notes TEXT,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                UNIQUE (watchlist_id, symbol)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS paper_orders (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL CHECK (side IN ('buy', 'sell')),
                quantity INTEGER NOT NULL CHECK (quantity > 0),
                order_type TEXT NOT NULL CHECK (order_type = 'market'),
                status TEXT NOT NULL CHECK (status IN ('filled', 'rejected')),
                requested_price DOUBLE PRECISION NOT NULL,
                fill_price DOUBLE PRECISION,
                submitted_at TIMESTAMP NOT NULL,
                filled_at TIMESTAMP,
                rejection_reason TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS paper_positions (
                user_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                quantity INTEGER NOT NULL CHECK (quantity > 0),
                average_cost DOUBLE PRECISION NOT NULL,
                realized_pnl DOUBLE PRECISION NOT NULL,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                PRIMARY KEY (user_id, symbol)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS paper_fills (
                id TEXT PRIMARY KEY,
                order_id TEXT NOT NULL REFERENCES paper_orders(id) ON DELETE CASCADE,
                user_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL CHECK (side IN ('buy', 'sell')),
                quantity INTEGER NOT NULL CHECK (quantity > 0),
                market_price DOUBLE PRECISION NOT NULL,
                fill_price DOUBLE PRECISION NOT NULL,
                realized_pnl DOUBLE PRECISION NOT NULL,
                filled_at TIMESTAMP NOT NULL
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_watchlists_user_id ON watchlists (user_id)",
            "CREATE INDEX IF NOT EXISTS idx_watchlist_items_watchlist_id ON watchlist_items (watchlist_id)",
            "CREATE INDEX IF NOT EXISTS idx_paper_orders_user_id ON paper_orders (user_id)",
            "CREATE INDEX IF NOT EXISTS idx_paper_positions_user_id ON paper_positions (user_id)",
            "CREATE INDEX IF NOT EXISTS idx_paper_fills_user_id ON paper_fills (user_id)"
        )
    ),
    Migration(
        identifier="0002_phase3_sessions_and_audit",
        description="users, sessions, audit events",
        statements=(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                handle TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                auth_provider TEXT NOT NULL,
                provider_subject TEXT NOT NULL,
                entitlement TEXT NOT NULL,
                execution_mode TEXT NOT NULL CHECK (execution_mode IN ('paper', 'live')),
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                UNIQUE (auth_provider, provider_subject)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                token_hash TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                last_seen_at TIMESTAMP NOT NULL,
                revoked_at TIMESTAMP,
                ip_address TEXT,
                user_agent TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS audit_events (
                id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                user_id TEXT,
                session_id TEXT,
                entity_type TEXT,
                entity_id TEXT,
                payload_json TEXT,
                created_at TIMESTAMP NOT NULL
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions (user_id)",
            "CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions (expires_at)",
            "CREATE INDEX IF NOT EXISTS idx_audit_events_user_id ON audit_events (user_id)",
            "CREATE INDEX IF NOT EXISTS idx_audit_events_event_type ON audit_events (event_type)"
        )
    ),
    Migration(
        identifier="0003_signal_tracking",
        description="persisted signal snapshots and alerts",
        statements=(
            """
            CREATE TABLE IF NOT EXISTS signal_snapshots (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                setup_type TEXT NOT NULL,
                action TEXT NOT NULL,
                entry_state TEXT NOT NULL,
                confidence INTEGER NOT NULL,
                score INTEGER NOT NULL,
                thesis TEXT NOT NULL,
                entry_price DOUBLE PRECISION,
                stop_loss DOUBLE PRECISION,
                take_profit1 DOUBLE PRECISION,
                take_profit2 DOUBLE PRECISION,
                market_data_source TEXT NOT NULL,
                market_data_quality TEXT NOT NULL,
                is_actionable INTEGER NOT NULL,
                has_position INTEGER NOT NULL,
                market_phase TEXT NOT NULL,
                regime_headline TEXT NOT NULL,
                reasons_json TEXT NOT NULL,
                warnings_json TEXT NOT NULL,
                signal_fingerprint TEXT NOT NULL,
                transition_json TEXT,
                snapshot_json TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS signal_alerts (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                symbol TEXT,
                snapshot_id TEXT REFERENCES signal_snapshots(id) ON DELETE SET NULL,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('new', 'read', 'acknowledged')),
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                dedupe_key TEXT NOT NULL,
                change_types_json TEXT NOT NULL,
                data_quality TEXT,
                payload_json TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                read_at TIMESTAMP,
                acknowledged_at TIMESTAMP
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_signal_snapshots_user_symbol_created_at ON signal_snapshots (user_id, symbol, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_signal_snapshots_user_created_at ON signal_snapshots (user_id, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_signal_snapshots_user_actionable_created_at ON signal_snapshots (user_id, is_actionable, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_signal_alerts_user_created_at ON signal_alerts (user_id, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_signal_alerts_user_status_created_at ON signal_alerts (user_id, status, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_signal_alerts_user_symbol_created_at ON signal_alerts (user_id, symbol, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_signal_alerts_user_dedupe_created_at ON signal_alerts (user_id, dedupe_key, created_at DESC)"
        )
    )
)


class MigrationManager:
    def __init__(self, target_database: Database) -> None:
        self.database = target_database

    def _ensure_migration_table(self, session: DatabaseSession) -> None:
        session.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                migration_id TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                applied_at TIMESTAMP NOT NULL
            )
            """
        )

    def _applied_ids(self, session: DatabaseSession) -> set[str]:
        self._ensure_migration_table(session)
        rows = session.fetchall("SELECT migration_id FROM schema_migrations")
        return {str(row["migration_id"]) for row in rows}

    def pending(self) -> list[Migration]:
        with self.database.session() as session:
            applied_ids = self._applied_ids(session)
        return [migration for migration in MIGRATIONS if migration.identifier not in applied_ids]

    def apply_pending(self) -> list[str]:
        applied: list[str] = []
        with self.database.session() as session:
            applied_ids = self._applied_ids(session)
            for migration in MIGRATIONS:
                if migration.identifier in applied_ids:
                    continue
                for statement in migration.statements:
                    session.execute(statement)
                session.execute(
                    """
                    INSERT INTO schema_migrations (migration_id, description, applied_at)
                    VALUES (:migration_id, :description, :applied_at)
                    """,
                    {
                        "migration_id": migration.identifier,
                        "description": migration.description,
                        "applied_at": utc_now_iso()
                    }
                )
                applied.append(migration.identifier)
        return applied

    def ensure_current(self) -> None:
        pending = self.pending()
        if pending:
            raise MigrationError()

    def status_lines(self) -> list[str]:
        pending = {migration.identifier for migration in self.pending()}
        lines: list[str] = []
        for migration in MIGRATIONS:
            state = "pending" if migration.identifier in pending else "applied"
            lines.append(f"{migration.identifier} {state} {migration.description}")
        return lines


def prepare_database() -> None:
    database.validate_configuration()
    database.ping()
    manager = MigrationManager(database)
    if settings.auto_apply_migrations:
        manager.apply_pending()
        return
    manager.ensure_current()


def main(argv: list[str] | None = None) -> int:
    args = argv or sys.argv[1:]
    command = args[0] if args else "status"
    manager = MigrationManager(database)

    if command == "apply":
        applied = manager.apply_pending()
        if applied:
            for migration_id in applied:
                print(f"applied {migration_id}")
        else:
            print("no pending migrations")
        return 0

    if command == "status":
        for line in manager.status_lines():
            print(line)
        return 0

    print("usage: python -m app.migrations [apply|status]")
    return 1


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())
