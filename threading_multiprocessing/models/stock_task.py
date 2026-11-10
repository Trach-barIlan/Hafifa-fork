"""
StockTask model.
"""

from dataclasses import dataclass
from datetime import datetime

try:
    from .stock_config import StockConfig
except ImportError:
    try:
        from models.stock_config import StockConfig
    except ImportError:
        from threading_multiprocessing.models.stock_config import StockConfig


@dataclass(frozen=True)
class StockTask:
    """A single stock data-mining task."""
    timestamp: datetime
    stock: StockConfig
