"""
Data loading utilities for reading timestamps and preparing stock tasks.
Conforms to the Stepdown Rule: caller functions are placed above helper functions.
"""

from datetime import datetime
from pathlib import Path
from typing import List, Sequence

try:
    from models import StockConfig, StockTask
except ImportError:
    from threading_multiprocessing.models import StockConfig, StockTask


def load_all_tasks(stocks: Sequence[StockConfig]) -> List[StockTask]:
    """
    Loads all stock tasks across all configured stocks.
    Top-level caller that aggregates tasks from each stock.
    """
    all_tasks: List[StockTask] = []
    for stock in stocks:
        all_tasks.extend(load_tasks_for_stock(stock))
    return all_tasks


def load_tasks_for_stock(stock: StockConfig) -> List[StockTask]:
    """
    Loads timestamps for a specific stock directly from its configured dates file.
    Helper called by load_all_tasks.
    """
    timestamps = read_timestamps(stock.dates_file)
    return [
        StockTask(timestamp=datetime.fromisoformat(timestamp), stock=stock)
        for timestamp in timestamps
    ]


def read_timestamps(file_path: Path) -> List[str]:
    """
    Reads non-empty timestamp lines from a text file.
    Low-level helper called by load_tasks_for_stock.
    """
    if not file_path.is_file():
        raise FileNotFoundError(f"Dates file not found: {file_path}")
    with open(file_path, "r", encoding="utf-8") as dates_file:
        return [stripped_line for line in dates_file if (stripped_line := line.strip())]
