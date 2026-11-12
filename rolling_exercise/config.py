"""Centralized application settings loaded from environment variables and .env file."""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    """Application settings with type validation and defaults."""

    # Server Configuration
    app_name: str = "Air Quality Monitoring API"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    debug: bool = False

    # Database Configuration
    database_url: str = f"sqlite:///{BASE_DIR / 'air_quality.db'}"

    # Logging Configuration
    log_level: str = "INFO"
    log_file: str = str(BASE_DIR / "logs" / "app.log")

    # Business Rules
    alert_aqi_threshold: float = 300.0

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
