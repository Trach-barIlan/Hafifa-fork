"""
StockConfig model.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class StockConfig:
    """Configuration mapping a stock name to its ticker and settings attribute."""
    name: str
    ticker: str
    settings_attribute: str

