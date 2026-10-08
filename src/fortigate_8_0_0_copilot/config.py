"""Application settings loaded from environment variables and the root .env file."""

"""
Create a Settings class for my application.
Look for a .env file in the project's root directory.
Read it using UTF-8.
Ignore settings that I haven't defined yet.
My app has an app_env setting that defaults to development.
My app has a log_level setting that must be a valid logging level and defaults to INFO.
Finally, create one settings object that the rest of my application can import.
"""

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    backend_base_url: str = "http://127.0.0.1:8000"
    backend_timeout_seconds: float = Field(default=10.0, gt=0)
    app_env: str = "development"
    log_level: Literal[
        "CRITICAL", "FATAL", "ERROR", "WARNING", "WARN", "INFO", "DEBUG", "NOTSET"
    ] = "INFO"


settings = Settings()
