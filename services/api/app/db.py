from __future__ import annotations

import re
import sqlite3
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from app.config import settings
from app.errors import ConfigurationError, DatabaseError


SQL_PARAM_PATTERN = re.compile(r":([A-Za-z_][A-Za-z0-9_]*)")


class DatabaseSession:
    def __init__(self, connection: Any, dialect: str) -> None:
        self._connection = connection
        self.dialect = dialect

    def _prepare_sql(self, sql: str) -> str:
        if self.dialect == "postgresql":
            return SQL_PARAM_PATTERN.sub(r"%(\1)s", sql)
        return sql

    def _execute_raw(
        self,
        sql: str,
        params: Mapping[str, object] | None = None
    ) -> Any:
        try:
            return self._connection.execute(self._prepare_sql(sql), params or {})
        except Exception as exc:  # pragma: no cover - exercised through callers
            raise DatabaseError() from exc

    def _fetch_rows(
        self,
        sql: str,
        params: Mapping[str, object] | None = None
    ) -> list[dict[str, Any]]:
        cursor = self._execute_raw(sql, params)
        rows = cursor.fetchall()
        return [dict(row) if not isinstance(row, dict) else row for row in rows]

    def fetchall(
        self,
        sql: str,
        params: Mapping[str, object] | None = None
    ) -> list[dict[str, Any]]:
        return self._fetch_rows(sql, params)

    def fetchone(
        self,
        sql: str,
        params: Mapping[str, object] | None = None
    ) -> dict[str, Any] | None:
        rows = self._fetch_rows(sql, params)
        return rows[0] if rows else None

    def execute(self, sql: str, params: Mapping[str, object] | None = None) -> None:
        self._execute_raw(sql, params)

    def commit(self) -> None:
        try:
            self._connection.commit()
        except Exception as exc:  # pragma: no cover - exercised through callers
            raise DatabaseError() from exc

    def rollback(self) -> None:
        try:
            self._connection.rollback()
        except Exception as exc:  # pragma: no cover - exercised through callers
            raise DatabaseError() from exc

    def close(self) -> None:
        self._connection.close()


class Database:
    def __init__(self, url: str) -> None:
        self.url = url

    @property
    def backend(self) -> str:
        return "sqlite" if self.url.startswith("sqlite:///") else "postgresql"

    @property
    def is_sqlite(self) -> bool:
        return self.backend == "sqlite"

    def validate_configuration(self) -> None:
        if settings.app_env != "development" and self.is_sqlite:
            raise ConfigurationError(
                code="production_requires_postgresql",
                message="Non-development deployments must use PostgreSQL for persistence."
            )

        if settings.app_env != "development" and settings.data_provider == "mock":
            raise ConfigurationError(
                code="production_requires_real_market_data_provider",
                message="Non-development deployments must use a real market data provider."
            )

        if settings.local_login_requires_token and not settings.local_auth_token:
            raise ConfigurationError(
                code="local_auth_token_required",
                message=(
                    "LOCAL_AUTH_TOKEN must be configured when SESSION_STRATEGY is "
                    "'local-token'."
                )
            )

        if (
            settings.app_env != "development"
            and settings.data_provider == "alpha_vantage"
            and not settings.alpha_vantage_api_key
        ):
            raise ConfigurationError(
                code="alpha_vantage_api_key_required",
                message=(
                    "ALPHA_VANTAGE_API_KEY must be configured when DATA_PROVIDER is "
                    "'alpha_vantage' outside development."
                )
            )

        if (
            settings.app_env != "development"
            and settings.data_provider == "alpha_vantage"
            and not settings.alpha_vantage_intraday_entitlement
        ):
            raise ConfigurationError(
                code="alpha_vantage_intraday_entitlement_required",
                message=(
                    "ALPHA_VANTAGE_INTRADAY_ENTITLEMENT must be configured when "
                    "DATA_PROVIDER is 'alpha_vantage' outside development."
                )
            )

    def _connect_sqlite(self) -> DatabaseSession:
        path_value = self.url.removeprefix("sqlite:///")
        path = Path(path_value)
        if path_value != ":memory:" and not path.is_absolute():
            path = (Path.cwd() / path).resolve()

        if path_value != ":memory:":
            path.parent.mkdir(parents=True, exist_ok=True)

        try:
            connection = sqlite3.connect(
                ":memory:" if path_value == ":memory:" else path,
                timeout=10
            )
        except sqlite3.Error as exc:  # pragma: no cover - connection failure path
            raise DatabaseError() from exc

        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return DatabaseSession(connection=connection, dialect="sqlite")

    def _connect_postgresql(self) -> DatabaseSession:
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:  # pragma: no cover - install-time guard
            raise ConfigurationError(
                code="psycopg_missing",
                message="psycopg is required when DATABASE_URL points to PostgreSQL."
            ) from exc

        try:
            connection = psycopg.connect(self.url, row_factory=dict_row)
        except Exception as exc:  # pragma: no cover - connection failure path
            raise DatabaseError() from exc
        return DatabaseSession(connection=connection, dialect="postgresql")

    @contextmanager
    def session(self) -> Iterator[DatabaseSession]:
        session = self._connect_sqlite() if self.is_sqlite else self._connect_postgresql()

        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def ping(self) -> None:
        with self.session() as session:
            session.fetchone("SELECT 1 AS ok")


database = Database(settings.database_url)


def get_db_session() -> Iterator[DatabaseSession]:
    with database.session() as session:
        yield session
