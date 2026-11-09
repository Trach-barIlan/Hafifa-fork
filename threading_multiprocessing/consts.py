"""
Constants and static configurations for stock price mining.
"""

from pathlib import Path
from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

try:
    from models import StockConfig
except ImportError:
    from threading_multiprocessing.models import StockConfig

BASE_DIR: Path = Path(__file__).resolve().parent

DEFAULT_MAX_WORKERS: int = 10
YFINANCE_INTERVAL: str = "1h"
LOG_FORMAT: str = "%(asctime)s [%(levelname)s] %(message)s"
LOG_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"

BITCOIN_TICKER: str = "BTC-USD"
GOOGLE_TICKER: str = "GOOGL"
AMAZON_TICKER: str = "AMZN"


class Settings(BaseSettings):
    """Application settings and environment variable configuration model."""
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bitcoin_dates: Path = Field(validation_alias=AliasChoices("BITCOIN_DATES", "TIMES_PATH"))
    google_dates: Path = Field(validation_alias=AliasChoices("GOOGLE_DATES"))
    amazon_dates: Path = Field(validation_alias=AliasChoices("AMAZON_DATES"))
    destination_file: Path = Field(validation_alias=AliasChoices("DESTINATION_FILE"))
    max_workers: int = Field(default=DEFAULT_MAX_WORKERS, validation_alias=AliasChoices("MAX_WORKERS"))

    @field_validator("bitcoin_dates", "google_dates", "amazon_dates", "destination_file", mode="after")
    @classmethod
    def resolve_relative_path(cls, file_path: Path) -> Path:
        """Converts relative paths to absolute paths resolved against BASE_DIR."""
        return file_path if file_path.is_absolute() else BASE_DIR / file_path

    @property
    def stocks(self) -> list[StockConfig]:
        """Returns the configured stocks bound to their validated file paths."""
        return [
            StockConfig(name="Bitcoin", ticker=BITCOIN_TICKER, dates_file=self.bitcoin_dates),
            StockConfig(name="Google", ticker=GOOGLE_TICKER, dates_file=self.google_dates),
            StockConfig(name="Amazon", ticker=AMAZON_TICKER, dates_file=self.amazon_dates),
        ]
