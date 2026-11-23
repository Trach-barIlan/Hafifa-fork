"""Row parsing and validation utilities for air quality data ingestion."""

from collections.abc import Mapping
from datetime import date
from typing import Any

import pandas as pd

from logging_config import logger


def validate_and_parse_row(
    row_idx: int,
    row: Mapping[str, Any],
) -> tuple[date, str, float, float, float] | None:
    """Validate a single row of air quality data.

    Logs a warning and returns None if the row contains missing or corrupted values.

    Args:
        row_idx: Zero-based row index for error reporting.
        row: Mapping containing a single row's fields.

    Returns:
        Tuple of (date, city, pm25, no2, co2) if valid, or None if invalid.
    """
    human_row_num = row_idx + 2  # Account for 1-based indexing + header row

    city = parse_city(row.get("city"), human_row_num)
    if city is None:
        return None

    parsed_date = parse_date(row.get("date"), human_row_num)
    if parsed_date is None:
        return None

    pollutants = parse_pollutants(row, city, human_row_num)
    if pollutants is None:
        return None

    return (
        parsed_date,
        city,
        pollutants["pm25"],
        pollutants["no2"],
        pollutants["co2"],
    )


def parse_city(city_val: Any, human_row_num: int) -> str | None:
    """Validate and extract city name."""
    if pd.isna(city_val) or not str(city_val).strip():
        logger.warning(
            f"Row {human_row_num} skipped: City name is missing or empty."
        )
        return None
    return str(city_val).strip()


def parse_date(date_val: Any, human_row_num: int) -> date | None:
    """Validate and parse date string into a date object."""
    if pd.isna(date_val):
        logger.warning(f"Row {human_row_num} skipped: Date is missing.")
        return None

    try:
        clean_date_str = str(date_val).strip().replace("_", "-")
        return pd.to_datetime(clean_date_str).date()
    except Exception as exc:
        logger.warning(
            f"Row {human_row_num} skipped: Invalid date format '{date_val}' ({exc})."
        )
        return None


def parse_pollutants(
    row: Mapping[str, Any],
    city: str,
    human_row_num: int,
) -> dict[str, float] | None:
    """Validate and parse numeric pollutant values (pm25, no2, co2)."""
    pollutants: dict[str, float] = {}
    for pollutant_name in ("pm25", "no2", "co2"):
        val = row.get(pollutant_name)
        if pd.isna(val):
            logger.warning(
                f"Row {human_row_num} ({city}) skipped: Missing value for pollutant '{pollutant_name}'."
            )
            return None

        try:
            numeric_val = float(val)
            if numeric_val < 0:
                logger.warning(
                    f"Row {human_row_num} ({city}) skipped: Pollutant '{pollutant_name}' has negative value ({numeric_val})."
                )
                return None
            pollutants[pollutant_name] = numeric_val
        except (ValueError, TypeError) as exc:
            logger.warning(
                f"Row {human_row_num} ({city}) skipped: Non-numeric value '{val}' for '{pollutant_name}' ({exc})."
            )
            return None

    return pollutants
