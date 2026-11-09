"""
StockConfig model.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StockConfig:
    """Configuration mapping a stock name to its ticker and resolved dates file path."""
    name: str
    ticker: str
    dates_file: Path
