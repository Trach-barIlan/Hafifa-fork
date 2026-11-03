from dataclasses import dataclass
import datetime
import logging
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Iterable

import pandas as pd
import yfinance as yf
from dotenv import load_dotenv

# Suppress noisy yfinance warnings for closed market hours
logging.getLogger("yfinance").setLevel(logging.CRITICAL)

MAX_WORKERS = 10


@dataclass(frozen=True)
class StockConfig:
    name: str
    ticker: str
    env_var: str


STOCK_CONFIGS = (
    StockConfig(name="Bitcoin", ticker="BTC-USD", env_var="BITCOIN_DATES"),
    StockConfig(name="Google", ticker="GOOGL", env_var="GOOGLE_DATES"),
    StockConfig(name="Amazon", ticker="AMZN", env_var="AMAZON_DATES"),
)


def resolve_path(file_path: str | Path, base_dir: Path) -> Path:
    """Resolves relative file paths against a base directory."""
    path = Path(file_path)
    return path if path.is_absolute() else base_dir / path


def read_timestamps(file_path: Path) -> list[str]:
    """Reads non-empty timestamp lines from a text file."""
    if not file_path.is_file():
        raise FileNotFoundError(f"Dates file not found: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def load_tasks_for_stock(stock: StockConfig, base_dir: Path) -> list[tuple[str, StockConfig]]:
    """Loads timestamps for a specific stock defined by its environment variable."""
    env_val = os.getenv(stock.env_var)
    if not env_val:
        raise ValueError(f"Required environment variable '{stock.env_var}' is not set.")

    file_path = resolve_path(env_val, base_dir)
    timestamps = read_timestamps(file_path)
    return [(ts, stock) for ts in timestamps]


def load_all_tasks(configs: Iterable[StockConfig], base_dir: Path) -> list[tuple[str, StockConfig]]:
    """Loads all timestamp tasks across all configured stocks."""
    all_tasks: list[tuple[str, StockConfig]] = []
    for config in configs:
        all_tasks.extend(load_tasks_for_stock(config, base_dir))
    return all_tasks


def calculate_percentage_change(open_price: float, close_price: float) -> float:
    """Calculates percentage change between open and close prices."""
    if open_price == 0:
        return 0.0
    return ((close_price - open_price) / open_price) * 100


def fetch_stock_data(timestamp: str, stock: StockConfig) -> dict[str, Any]:
    """
    Fetches the 1-hour candle for a stock at the given timestamp and computes percentage change.
    """
    dt = datetime.datetime.fromisoformat(timestamp.strip())
    start = dt.replace(second=0, microsecond=0)
    end = start + datetime.timedelta(hours=1)

    ticker = yf.Ticker(stock.ticker)
    data = ticker.history(start=start, end=end, interval="1h", prepost=True)

    if data.empty:
        return {
            "hour": timestamp,
            "stock type": stock.name,
            "percentage change": None,
        }

    open_price = float(data["Open"].iloc[0])
    close_price = float(data["Close"].iloc[0])
    pct_change = calculate_percentage_change(open_price, close_price)

    return {
        "hour": timestamp,
        "stock type": stock.name,
        "percentage change": pct_change,
    }


def execute_parallel_fetching(
    tasks: list[tuple[str, StockConfig]], 
    max_workers: int = MAX_WORKERS
) -> list[dict[str, Any]]:
    """Fetches stock data in parallel using a ThreadPoolExecutor."""
    results: list[dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_task = {
            executor.submit(fetch_stock_data, timestamp, stock): (timestamp, stock.name)
            for timestamp, stock in tasks
        }

        for future in as_completed(future_to_task):
            ts, stock_name = future_to_task[future]
            try:
                result = future.result()
                results.append(result)
                print(result)
            except Exception as exc:
                print(f"[{stock_name}] {ts} generated an exception: {exc}")

    return results


def save_results(results: list[dict[str, Any]], destination_file: Path) -> None:
    """Saves results list to a CSV file using pandas."""
    if not results:
        print("No results to save.")
        return
    df = pd.DataFrame(results)
    df.to_csv(destination_file, index=False)
    print(f"Successfully saved {len(results)} rows to {destination_file}")


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    load_dotenv(base_dir / ".env")

    dest_env = os.getenv("DESTINATION_FILE")
    if not dest_env:
        print("Error: DESTINATION_FILE environment variable is not set.")
        return

    dest_file = resolve_path(dest_env, base_dir)

    try:
        tasks = load_all_tasks(STOCK_CONFIGS, base_dir)
    except (ValueError, FileNotFoundError) as err:
        print(f"Initialization error: {err}")
        return

    print(f"Fetching data for {len(tasks)} tasks using {MAX_WORKERS} workers...")
    results = execute_parallel_fetching(tasks, max_workers=MAX_WORKERS)
    save_results(results, dest_file)


if __name__ == "__main__":
    main()
