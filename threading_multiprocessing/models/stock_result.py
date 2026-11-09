"""
StockResult model.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class StockResult:
    """The result of an hourly stock price change calculation."""
    hour: str
    stock_type: str
    percentage_change: float | None

    def to_csv_dict(self) -> dict[str, str | float | None]:
        """Formats the result dictionary to match requested CSV column names."""
        return {
            "hour": self.hour,
            "stock type": self.stock_type,
            "percentage change": self.percentage_change,
        }

