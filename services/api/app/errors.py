from __future__ import annotations

import logging
from dataclasses import dataclass


logger = logging.getLogger("unveni.api")


@dataclass
class AppError(Exception):
    code: str
    message: str
    status_code: int
    log_level: int = logging.INFO

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


class AuthenticationError(AppError):
    def __init__(self, code: str, message: str, status_code: int = 401) -> None:
        super().__init__(code=code, message=message, status_code=status_code)


class AuthorizationError(AppError):
    def __init__(self, code: str, message: str, status_code: int = 403) -> None:
        super().__init__(code=code, message=message, status_code=status_code)


class DatabaseError(AppError):
    def __init__(
        self,
        code: str = "database_unavailable",
        message: str = "Database access is currently unavailable.",
        status_code: int = 503
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            status_code=status_code,
            log_level=logging.ERROR
        )


class ConfigurationError(AppError):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 500
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            status_code=status_code,
            log_level=logging.ERROR
        )


class MigrationError(AppError):
    def __init__(
        self,
        code: str = "database_migrations_required",
        message: str = (
            "Database migrations are pending. Run 'python -m app.migrations apply' "
            "before starting the API."
        ),
        status_code: int = 503
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            status_code=status_code,
            log_level=logging.ERROR
        )
