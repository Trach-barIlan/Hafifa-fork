"""
Stock price fetching and parallel execution utilities.
Conforms to the Stepdown Rule: caller functions are placed above helper functions.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
import logging
from typing import List, Sequence, Tuple

import yfinance as yf

try:
    from consts import DEFAULT_MAX_WORKERS, YFINANCE_INTERVAL
    from models import StockResult, StockTask
except ImportError:
    from threading_multiprocessing.consts import DEFAULT_MAX_WORKERS, YFINANCE_INTERVAL
    from threading_multiprocessing.models import StockResult, StockTask

logger = logging.getLogger(__name__)


def execute_parallel_fetching(
    tasks: Sequence[StockTask], 
    max_workers: int = DEFAULT_MAX_WORKERS
) -> List[StockResult]:
    """
    Fetches stock data in parallel using a ThreadPoolExecutor.
    Top-level coordinator that calls fetch_stock_data for each task.
    """
    results: List[StockResult] = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_task = {
            executor.submit(fetch_stock_data, task): task
            for task in tasks
        }

        for future in as_completed(future_to_task):
            task = future_to_task[future]
            try:
                result = future.result()
                results.append(result)
                logger.info("%s", result.to_csv_dict())
            except Exception as exception:
                logger.error("[%s] %s generated an exception: %s", task.stock.name, task.timestamp, exception)

    return results


def fetch_stock_data(task: StockTask) -> StockResult:
    """
    Fetches the 1-hour candle for a stock at the given timestamp and computes percentage change.
    Helper called by execute_parallel_fetching.
    """
    start_time, end_time = calculate_time_window(task.timestamp)

    ticker = yf.Ticker(task.stock.ticker)
    history_data = ticker.history(
        start=start_time,
        end=end_time,
        interval=YFINANCE_INTERVAL,
        prepost=True,
    )

    if history_data.empty:
        return StockResult(
            hour=task.timestamp,
            stock_type=task.stock.name,
            percentage_change=None,
        )

    open_price = float(history_data["Open"].iloc[0])
    close_price = float(history_data["Close"].iloc[0])
    percentage_change = calculate_percentage_change(open_price, close_price)

    return StockResult(
        hour=task.timestamp,
        stock_type=task.stock.name,
        percentage_change=percentage_change,
    )


def calculate_time_window(timestamp: datetime) -> Tuple[datetime, datetime]:
    """
    Calculates the 1-hour window (start and end times) for a given timestamp.
    Helper called by fetch_stock_data.
    """
    start_time = timestamp.replace(second=0, microsecond=0)
    end_time = start_time + timedelta(hours=1)
    return start_time, end_time


def calculate_percentage_change(open_price: float, close_price: float) -> float:
    """
    Calculates percentage change between open and close prices.
    Helper called by fetch_stock_data.
    """
    if open_price == 0:
        return 0.0
    return ((close_price - open_price) / open_price) * 100
