"""Service for reading, validating, and ingesting air quality CSV files."""

from dataclasses import dataclass
from datetime import date
from io import BytesIO, StringIO
from typing import BinaryIO, TextIO, Union

import pandas as pd
from sqlalchemy.orm import Session

from calculate_aqi import calculate_aqi
from config import settings
from logging_config import logger
from models import AirQualityRecord, Alert

ALERT_AQI_THRESHOLD = settings.alert_aqi_threshold


COLUMN_MAPPING = {
    "date": "date",
    "city": "city",
    "pm2.5": "pm25",
    "pm25": "pm25",
    "no2": "no2",
    "co2": "co2",
}


@dataclass
class IngestionResult:
    """Summary of the CSV ingestion process."""

    total_rows: int
    valid_rows: int
    corrupted_rows: int
    alerts_generated: int


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize DataFrame column names to standard lowercase identifiers.

    Args:
        df: Input raw DataFrame.

    Returns:
        pd.DataFrame: DataFrame with normalized column names.
    """
    normalized_cols = {col: str(col).strip().lower() for col in df.columns}
    df = df.rename(columns=normalized_cols)

    mapped_cols = {
        col: COLUMN_MAPPING[col] for col in df.columns if col in COLUMN_MAPPING
    }
    return df.rename(columns=mapped_cols)


def _validate_and_parse_row(
    row_idx: int,
    row: pd.Series,
) -> Union[tuple[date, str, float, float, float], None]:
    """Validate a single row of air quality data.

    Logs a warning and returns None if the row contains missing or corrupted values.

    Args:
        row_idx: Zero-based row index for error reporting.
        row: Series containing a single row's fields.

    Returns:
        Tuple of (date, city, pm25, no2, co2) if valid, or None if invalid.
    """
    human_row_num = row_idx + 2  # Account for 1-based indexing + header row

    # Validate city
    city_val = row.get("city")
    if pd.isna(city_val) or not str(city_val).strip():
        logger.warning(
            "Row %d skipped: City name is missing or empty.", human_row_num
        )
        return None
    city = str(city_val).strip()

    # Validate date
    date_val = row.get("date")
    if pd.isna(date_val):
        logger.warning("Row %d skipped: Date is missing.", human_row_num)
        return None

    try:
        # Replaces possible underscore with hyphen for YYYY_MM_DD format
        clean_date_str = str(date_val).strip().replace("_", "-")
        parsed_date = pd.to_datetime(clean_date_str).date()
    except Exception as exc:
        logger.warning(
            "Row %d skipped: Invalid date format '%s' (%s).",
            human_row_num,
            date_val,
            exc,
        )
        return None

    # Validate pollutant levels
    pollutants: dict[str, float] = {}
    for pollutant_name in ("pm25", "no2", "co2"):
        val = row.get(pollutant_name)
        if pd.isna(val):
            logger.warning(
                "Row %d (%s) skipped: Missing value for pollutant '%s'.",
                human_row_num,
                city,
                pollutant_name,
            )
            return None

        try:
            numeric_val = float(val)
            if numeric_val < 0:
                logger.warning(
                    "Row %d (%s) skipped: Pollutant '%s' has negative value (%f).",
                    human_row_num,
                    city,
                    pollutant_name,
                    numeric_val,
                )
                return None
            pollutants[pollutant_name] = numeric_val
        except (ValueError, TypeError) as exc:
            logger.warning(
                "Row %d (%s) skipped: Non-numeric value '%s' for '%s' (%s).",
                human_row_num,
                city,
                val,
                pollutant_name,
                exc,
            )
            return None

    return (
        parsed_date,
        city,
        pollutants["pm25"],
        pollutants["no2"],
        pollutants["co2"],
    )


def process_air_quality_csv(
    file_content: Union[str, bytes, BinaryIO, TextIO],
    db: Session,
) -> IngestionResult:
    """Read, clean, calculate AQI, and store records from a CSV file.

    Corrupted or missing rows are logged and ignored.
    If calculated AQI > 300, an Alert record is created.

    Args:
        file_content: File path, bytes, or file-like stream of the CSV.
        db: Active SQLAlchemy database session.

    Returns:
        IngestionResult: Summary counts of processed records.

    Raises:
        ValueError: If file content is empty or cannot be parsed as CSV.
    """
    logger.info("Beginning air quality CSV data ingestion.")

    try:
        if isinstance(file_content, bytes):
            stream = BytesIO(file_content)
            df = pd.read_csv(stream)
        elif isinstance(file_content, str):
            if "\n" in file_content or "\r" in file_content:
                stream = StringIO(file_content)
                df = pd.read_csv(stream)
            else:
                df = pd.read_csv(file_content)
        else:
            df = pd.read_csv(file_content)
    except Exception as exc:
        logger.error("Failed to parse CSV file: %s", exc)
        raise ValueError(f"Could not parse CSV content: {exc}") from exc

    df = _normalize_columns(df)
    required_columns = {"date", "city", "pm25", "no2", "co2"}
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        err_msg = f"CSV is missing required columns: {sorted(missing_columns)}"
        logger.error(err_msg)
        raise ValueError(err_msg)

    total_rows = len(df)
    records_to_insert: list[AirQualityRecord] = []
    alerts_to_insert: list[Alert] = []

    for idx, row in df.iterrows():
        validated_data = _validate_and_parse_row(idx, row)
        if validated_data is None:
            continue

        record_date, city, pm25, no2, co2 = validated_data

        # Calculate AQI and AQI level using the provided calculate_aqi function
        aqi_value, aqi_level = calculate_aqi(pm25, no2, co2)
        logger.info(
            "Calculated AQI for %s on %s: AQI=%.1f (%s)",
            city,
            record_date,
            aqi_value,
            aqi_level,
        )

        record = AirQualityRecord(
            date=record_date,
            city=city,
            pm25=pm25,
            no2=no2,
            co2=co2,
            aqi=aqi_value,
            aqi_level=aqi_level,
        )
        records_to_insert.append(record)

        if aqi_value > ALERT_AQI_THRESHOLD:
            logger.warning(
                "High pollution alert triggered! City: %s, Date: %s, AQI: %.1f",
                city,
                record_date,
                aqi_value,
            )
            alert = Alert(
                date=record_date,
                city=city,
                aqi=aqi_value,
            )
            alerts_to_insert.append(alert)

    # Persist in a single database transaction
    if records_to_insert:
        db.add_all(records_to_insert)
    if alerts_to_insert:
        db.add_all(alerts_to_insert)

    db.commit()

    valid_count = len(records_to_insert)
    corrupted_count = total_rows - valid_count
    alerts_count = len(alerts_to_insert)

    logger.info(
        "Ingestion completed: Total=%d, Valid=%d, Corrupted=%d, Alerts=%d",
        total_rows,
        valid_count,
        corrupted_count,
        alerts_count,
    )

    return IngestionResult(
        total_rows=total_rows,
        valid_rows=valid_count,
        corrupted_rows=corrupted_count,
        alerts_generated=alerts_count,
    )
