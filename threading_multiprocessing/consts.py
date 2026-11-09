"""
Constants and static configurations for stock price mining.
"""

from pathlib import Path

try:
    from models import StockConfig
except ImportError:
    from threading_multiprocessing.models import StockConfig

BASE_DIR: Path = Path(__file__).resolve().parent

DEFAULT_MAX_WORKERS: int = 10
YFINANCE_INTERVAL: str = "1h"
LOG_FORMAT: str = "%(asctime)s [%(levelname)s] %(message)s"
LOG_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"

STOCK_CONFIGS: tuple[StockConfig, ...] = (
    StockConfig(name="Bitcoin", ticker="BTC-USD", settings_attribute="bitcoin_dates"),
    StockConfig(name="Google", ticker="GOOGL", settings_attribute="google_dates"),
    StockConfig(name="Amazon", ticker="AMZN", settings_attribute="amazon_dates"),
)
