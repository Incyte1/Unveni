from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE_URL = f"sqlite:///{(BASE_DIR / '.data' / 'unveni.db').as_posix()}"
SessionStrategy = Literal["development", "local-token", "external"]
DataProvider = Literal["mock", "alpha_vantage"]
IntradayEntitlement = Literal["delayed", "realtime"]


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_env: str
    cors_origins: tuple[str, ...]
    data_provider: DataProvider
    default_entitlement: str
    default_execution_mode: str
    session_strategy: SessionStrategy
    database_url: str
    local_auth_token: str | None
    alpha_vantage_api_key: str | None
    alpha_vantage_intraday_entitlement: IntradayEntitlement | None
    market_data_timeout_seconds: float
    session_cookie_name: str = "unveni_session"
    session_ttl_hours: int = 24 * 7

    @classmethod
    def from_env(cls) -> "Settings":
        app_env = os.getenv("APP_ENV", "development")
        raw_provider = os.getenv("DATA_PROVIDER", "mock").strip().lower()
        raw_strategy = os.getenv(
            "SESSION_STRATEGY",
            "development" if app_env == "development" else "local-token"
        ).strip()
        allowed_providers: tuple[DataProvider, ...] = (
            "mock",
            "alpha_vantage"
        )
        allowed_strategies: tuple[SessionStrategy, ...] = (
            "development",
            "local-token",
            "external"
        )
        raw_intraday_entitlement = os.getenv(
            "ALPHA_VANTAGE_INTRADAY_ENTITLEMENT",
            "delayed"
        ).strip().lower()
        allowed_intraday_entitlements: tuple[IntradayEntitlement, ...] = (
            "delayed",
            "realtime"
        )
        if raw_provider not in allowed_providers:
            raise ValueError(
                f"Unsupported DATA_PROVIDER '{raw_provider}'. "
                f"Expected one of {', '.join(allowed_providers)}."
            )
        if raw_strategy not in allowed_strategies:
            raise ValueError(
                f"Unsupported SESSION_STRATEGY '{raw_strategy}'. "
                f"Expected one of {', '.join(allowed_strategies)}."
            )
        if raw_intraday_entitlement and raw_intraday_entitlement not in allowed_intraday_entitlements:
            raise ValueError(
                f"Unsupported ALPHA_VANTAGE_INTRADAY_ENTITLEMENT '{raw_intraday_entitlement}'. "
                f"Expected one of {', '.join(allowed_intraday_entitlements)}."
            )

        origins = tuple(
            origin.strip()
            for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
            if origin.strip()
        )
        return cls(
            app_name=os.getenv("APP_NAME", "Unveni API"),
            app_env=app_env,
            cors_origins=origins,
            data_provider=raw_provider,
            default_entitlement="delayed-demo",
            default_execution_mode="paper",
            session_strategy=raw_strategy,
            database_url=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
            local_auth_token=os.getenv("LOCAL_AUTH_TOKEN"),
            alpha_vantage_api_key=os.getenv("ALPHA_VANTAGE_API_KEY"),
            alpha_vantage_intraday_entitlement=(
                raw_intraday_entitlement if raw_intraday_entitlement else None
            ),
            market_data_timeout_seconds=float(os.getenv("MARKET_DATA_TIMEOUT_SECONDS", "8"))
        )

    @property
    def auto_apply_migrations(self) -> bool:
        return self.app_env == "development"

    @property
    def use_secure_cookies(self) -> bool:
        return self.app_env != "development"

    @property
    def database_backend(self) -> Literal["sqlite", "postgresql"]:
        return "sqlite" if self.database_url.startswith("sqlite:///") else "postgresql"

    @property
    def local_login_requires_token(self) -> bool:
        return self.session_strategy == "local-token"

    @property
    def allow_market_data_fallback(self) -> bool:
        return self.app_env == "development"


settings = Settings.from_env()
