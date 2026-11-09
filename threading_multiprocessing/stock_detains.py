"""
Stock Price Mining Exercise - Multithreading.

Fetches hourly stock data for configured stock types (Bitcoin, Google, Amazon)
using yfinance and computes percentage change concurrently.
Configured via Pydantic BaseSettings (pydantic-settings).
Conforms to Python Clean Code standards (zedr/clean-code-python).
"""

from datetime import datetime, timedelta
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Sequence, Tuple

import pandas as pd
from pydantic import ValidationError
import yfinance as yf

try:
    from consts import (
        DEFAULT_MAX_WORKERS,
        LOG_DATE_FORMAT,
        LOG_FORMAT,
        YFINANCE_INTERVAL,
        Settings,
    )
    from models import StockConfig, StockResult, StockTask
except ImportError:
    from threading_multiprocessing.consts import (
        DEFAULT_MAX_WORKERS,
        LOG_DATE_FORMAT,
        LOG_FORMAT,
        YFINANCE_INTERVAL,
        Settings,
    )
    from threading_multiprocessing.models import StockConfig, StockResult, StockTask

logger = logging.getLogger(__name__)


def configure_environment() -> None:
    """Sets up global logging configuration and silences external warning noise."""
    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
    )
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)


def read_timestamps(file_path: Path) -> List[str]:
    """Reads non-empty timestamp lines from a text file."""
    if not file_path.is_file():
        raise FileNotFoundError(f"Dates file not found: {file_path}")
    with open(file_path, "r", encoding="utf-8") as dates_file:
        return [stripped_line for line in dates_file if (stripped_line := line.strip())]


def load_tasks_for_stock(stock: StockConfig) -> List[StockTask]:
    """Loads timestamps for a specific stock directly from its configured dates file."""
    timestamps = read_timestamps(stock.dates_file)
    return [
        StockTask(timestamp=datetime.fromisoformat(timestamp), stock=stock)
        for timestamp in timestamps
    ]


def load_all_tasks(stocks: Sequence[StockConfig]) -> List[StockTask]:
    """Loads all stock tasks across all configured stocks."""
    all_tasks: List[StockTask] = []
    for stock in stocks:
        all_tasks.extend(load_tasks_for_stock(stock))
    return all_tasks


def calculate_percentage_change(open_price: float, close_price: float) -> float:
    """Calculates percentage change between open and close prices."""
    if open_price == 0:
        return 0.0
    return ((close_price - open_price) / open_price) * 100


def calculate_time_window(timestamp: datetime) -> Tuple[datetime, datetime]:
    """Calculates the 1-hour window (start and end times) for a given timestamp."""
    start_time = timestamp.replace(second=0, microsecond=0)
    end_time = start_time + timedelta(hours=1)
    return start_time, end_time


def fetch_stock_data(task: StockTask) -> StockResult:
    """
    Fetches the 1-hour candle for a stock at the given timestamp and computes percentage change.
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


def execute_parallel_fetching(
    tasks: Sequence[StockTask], 
    max_workers: int = DEFAULT_MAX_WORKERS
) -> List[StockResult]:
    """Fetches stock data in parallel using a ThreadPoolExecutor."""
    results = []

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


def save_results(results: Sequence[StockResult], destination_file: Path) -> None:
    """Saves results list to a CSV file using pandas."""
    if results:
        formatted_rows = [result.to_csv_dict() for result in results]
        data_frame = pd.DataFrame(formatted_rows)
        data_frame.to_csv(destination_file, index=False)
        logger.info("Successfully saved %d rows to %s", len(results), destination_file)
    else:
        logger.warning("No results to save.")


def main() -> None:
    """Main program execution."""
    configure_environment()

    try:
        settings = Settings()
    except ValidationError as error:
        logger.error("Configuration error: %s", error)
        return

    try:
        tasks = load_all_tasks(settings.stocks)
    except FileNotFoundError as error:
        logger.error("File error: %s", error)
        return

    logger.info("Fetching data for %d tasks using %d workers...", len(tasks), settings.max_workers)
    results = execute_parallel_fetching(tasks, max_workers=settings.max_workers)
    save_results(results, settings.destination_file)


if __name__ == "__main__":
    main()
