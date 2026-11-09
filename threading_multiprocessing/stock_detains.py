"""
Stock Price Mining Exercise - Multithreading.

Fetches hourly stock data for configured stock types (Bitcoin, Google, Amazon)
using yfinance and computes percentage change concurrently.
Conforms to Python Clean Code standards (zedr/clean-code-python).
"""

from dataclasses import dataclass
import datetime
import logging
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterable

import pandas as pd
import yfinance as yf
from dotenv import load_dotenv

MAX_WORKERS: int = 10
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StockConfig:
    """Configuration mapping a stock name to its ticker and environment variable."""
    name: str
    ticker: str
    env_var: str


@dataclass(frozen=True)
class StockTask:
    """A single stock data-mining task."""
    timestamp: str
    stock: StockConfig


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


STOCK_CONFIGS: tuple[StockConfig, ...] = (
    StockConfig(name="Bitcoin", ticker="BTC-USD", env_var="BITCOIN_DATES"),
    StockConfig(name="Google", ticker="GOOGL", env_var="GOOGLE_DATES"),
    StockConfig(name="Amazon", ticker="AMZN", env_var="AMAZON_DATES"),
)


def configure_environment() -> None:
    """Sets up global logging configuration and silences external warning noise."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)


def resolve_path(file_path: str | Path, base_dir: Path) -> Path:
    """Resolves relative file paths against a base directory."""
    candidate_path = Path(file_path)
    if candidate_path.is_absolute():
        return candidate_path
    return base_dir / candidate_path


def read_timestamps(file_path: Path) -> list[str]:
    """Reads non-empty timestamp lines from a text file."""
    if not file_path.is_file():
        raise FileNotFoundError(f"Dates file not found: {file_path}")
    with open(file_path, "r", encoding="utf-8") as dates_file:
        return [stripped_line for line in dates_file if (stripped_line := line.strip())]


def load_tasks_for_stock(stock: StockConfig, base_dir: Path) -> list[StockTask]:
    """Loads timestamps for a specific stock defined by its environment variable."""
    environment_value = os.getenv(stock.env_var)
    if not environment_value:
        raise ValueError(f"Required environment variable '{stock.env_var}' is not set.")

    file_path = resolve_path(environment_value, base_dir)
    timestamps = read_timestamps(file_path)
    return [StockTask(timestamp=timestamp, stock=stock) for timestamp in timestamps]


def load_all_tasks(configs: Iterable[StockConfig], base_dir: Path) -> list[StockTask]:
    """Loads all stock tasks across all configured stocks."""
    all_tasks: list[StockTask] = []
    for config in configs:
        all_tasks.extend(load_tasks_for_stock(config, base_dir))
    return all_tasks


def calculate_percentage_change(open_price: float, close_price: float) -> float:
    """Calculates percentage change between open and close prices."""
    if open_price == 0:
        return 0.0
    return ((close_price - open_price) / open_price) * 100


def fetch_stock_data(task: StockTask) -> StockResult:
    """
    Fetches the 1-hour candle for a stock at the given timestamp and computes percentage change.
    """
    parsed_datetime = datetime.datetime.fromisoformat(task.timestamp.strip())
    start_time = parsed_datetime.replace(second=0, microsecond=0)
    end_time = start_time + datetime.timedelta(hours=1)

    ticker = yf.Ticker(task.stock.ticker)
    history_data = ticker.history(start=start_time, end=end_time, interval="1h", prepost=True)

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
    tasks: list[StockTask], 
    max_workers: int = MAX_WORKERS
) -> list[StockResult]:
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


def save_results(results: list[StockResult], destination_file: Path) -> None:
    """Saves results list to a CSV file using pandas."""
    if not results:
        logger.warning("No results to save.")
        return
    formatted_rows = [result.to_csv_dict() for result in results]
    data_frame = pd.DataFrame(formatted_rows)
    data_frame.to_csv(destination_file, index=False)
    logger.info("Successfully saved %d rows to %s", len(results), destination_file)


def main() -> None:
    """Main program execution."""
    configure_environment()

    base_dir = Path(__file__).resolve().parent
    load_dotenv(base_dir / ".env")

    destination_env = os.getenv("DESTINATION_FILE")
    if not destination_env:
        logger.error("DESTINATION_FILE environment variable is not set.")
        return

    destination_file = resolve_path(destination_env, base_dir)

    try:
        tasks = load_all_tasks(STOCK_CONFIGS, base_dir)
    except (ValueError, FileNotFoundError) as error:
        logger.error("Initialization error: %s", error)
        return

    logger.info("Fetching data for %d tasks using %d workers...", len(tasks), MAX_WORKERS)
    results = execute_parallel_fetching(tasks, max_workers=MAX_WORKERS)
    save_results(results, destination_file)


if __name__ == "__main__":
    main()
