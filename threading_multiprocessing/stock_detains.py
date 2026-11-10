"""
Stock Price Mining Exercise - Multithreading.

Main entry point orchestrating stock data mining workflow.
Conforms to Python Clean Code standards (Stepdown Rule: callers above callees).
"""

import logging

from pydantic import ValidationError

try:
    from consts import LOG_DATE_FORMAT, LOG_FORMAT, Settings
    from csv_exporter import save_results
    from stock_fetcher import (
        calculate_percentage_change,
        calculate_time_window,
        execute_parallel_fetching,
        fetch_stock_data,
    )
    from task_loader import load_all_tasks, load_tasks_for_stock, read_timestamps
except ImportError:
    from threading_multiprocessing.consts import LOG_DATE_FORMAT, LOG_FORMAT, Settings
    from threading_multiprocessing.csv_exporter import save_results
    from threading_multiprocessing.stock_fetcher import (
        calculate_percentage_change,
        calculate_time_window,
        execute_parallel_fetching,
        fetch_stock_data,
    )
    from threading_multiprocessing.task_loader import (
        load_all_tasks,
        load_tasks_for_stock,
        read_timestamps,
    )

logger = logging.getLogger(__name__)


def main() -> None:
    """
    Main program execution.
    Top-level orchestrator calling helpers in sequential stepdown order.
    """
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


def configure_environment() -> None:
    """
    Sets up global logging configuration and silences external warning noise.
    Helper called by main.
    """
    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
    )
    import yfinance as yf
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)


if __name__ == "__main__":
    main()
