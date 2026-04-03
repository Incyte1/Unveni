from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_env: str
    cors_origins: tuple[str, ...]
    data_provider: str

    @classmethod
    def from_env(cls) -> "Settings":
        origins = tuple(
            origin.strip()
            for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
            if origin.strip()
        )
        return cls(
            app_name=os.getenv("APP_NAME", "Unveni API"),
            app_env=os.getenv("APP_ENV", "development"),
            cors_origins=origins,
            data_provider=os.getenv("DATA_PROVIDER", "mock")
        )


settings = Settings.from_env()
