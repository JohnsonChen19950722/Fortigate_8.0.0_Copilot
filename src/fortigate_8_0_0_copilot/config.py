"""Application settings loaded from environment variables and the root .env file."""

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    log_level: Literal[
        "CRITICAL", "FATAL", "ERROR", "WARNING", "WARN", "INFO", "DEBUG", "NOTSET"
    ] = "INFO"


settings = Settings()
