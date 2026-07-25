"""Application settings loaded from environment / .env (docs/config/System-Config.md)."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """AERA runtime settings — every field maps to an AERA_* env var."""

    model_config = SettingsConfigDict(
        env_prefix="AERA_", env_file=".env", extra="ignore"
    )

    env: str = "development"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"
    secret_key: str = "change-me"
    memory_db: str = "data/aera.db"

    @property
    def is_development(self) -> bool:
        return self.env == "development"


settings = Settings()
