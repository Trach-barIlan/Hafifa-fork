"""
CSV export utilities for stock mining results.
"""

import logging
from pathlib import Path
from typing import Sequence

import pandas as pd

try:
    from models import StockResult
except ImportError:
    from threading_multiprocessing.models import StockResult

logger = logging.getLogger(__name__)


def save_results(results: Sequence[StockResult], destination_file: Path) -> None:
    """Saves results list to a CSV file using pandas."""
    if results:
        formatted_rows = [result.to_csv_dict() for result in results]
        data_frame = pd.DataFrame(formatted_rows)
        data_frame.to_csv(destination_file, index=False)
        logger.info("Successfully saved %d rows to %s", len(results), destination_file)
    else:
        logger.warning("No results to save.")
