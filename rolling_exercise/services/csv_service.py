"""Service for reading, validating, and ingesting air quality CSV files."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from io import BytesIO, StringIO
from typing import Any, BinaryIO, TextIO

import pandas as pd
from sqlalchemy import select
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


def process_air_quality_csv(
    file_content: str | bytes | BinaryIO | TextIO,
    db: Session,
) -> IngestionResult:
    """Read, clean, calculate AQI, and store records from a CSV file.

    Corrupted or missing rows are logged and ignored.
    If calculated AQI > 300, an Alert record is created and linked via foreign key.
    Duplicate (city, date) entries are upserted cleanly.

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
    valid_count = 0
    alerts_generated_count = 0

    rows_data = df.to_dict(orient="records")

    # Validate and parse all rows in memory
    valid_parsed_rows: list[tuple[date, str, float, float, float]] = []
    for idx, row in enumerate(rows_data):
        validated_data = _validate_and_parse_row(idx, row)
        if validated_data is not None:
            valid_parsed_rows.append(validated_data)

    if not valid_parsed_rows:
        return IngestionResult(
            total_rows=total_rows,
            valid_rows=0,
            corrupted_rows=total_rows,
            alerts_generated=0,
        )

    # Batch-load existing records and alerts in 2 queries
    distinct_dates = {rec[0] for rec in valid_parsed_rows}
    existing_records = {
        (rec.city.lower(), rec.date): rec
        for rec in db.scalars(
            select(AirQualityRecord).where(AirQualityRecord.date.in_(distinct_dates))
        ).all()
    }
    existing_alerts = {
        (alert.city.lower(), alert.date): alert
        for alert in db.scalars(
            select(Alert).where(Alert.date.in_(distinct_dates))
        ).all()
    }

    for record_date, city, pm25, no2, co2 in valid_parsed_rows:
        valid_count += 1
        key = (city.lower(), record_date)

        # Calculate AQI and AQI level
        aqi_value, aqi_level = calculate_aqi(pm25, no2, co2)
        logger.info(
            "Calculated AQI for %s on %s: AQI=%.1f (%s)",
            city,
            record_date,
            aqi_value,
            aqi_level,
        )

        existing_record = existing_records.get(key)
        if existing_record:
            existing_record.pm25 = pm25
            existing_record.no2 = no2
            existing_record.co2 = co2
            existing_record.aqi = aqi_value
            existing_record.aqi_level = aqi_level
            target_record = existing_record
            logger.info("Updated existing record for %s on %s", city, record_date)
        else:
            target_record = AirQualityRecord(
                date=record_date,
                city=city,
                pm25=pm25,
                no2=no2,
                co2=co2,
                aqi=aqi_value,
                aqi_level=aqi_level,
            )
            db.add(target_record)
            existing_records[key] = target_record

        existing_alert = existing_alerts.get(key)
        if aqi_value > ALERT_AQI_THRESHOLD:
            logger.warning(
                "High pollution alert triggered! City: %s, Date: %s, AQI: %.1f",
                city,
                record_date,
                aqi_value,
            )
            if existing_alert:
                existing_alert.aqi = aqi_value
                existing_alert.record = target_record
            else:
                alert = Alert(
                    record=target_record,
                    date=record_date,
                    city=city,
                    aqi=aqi_value,
                )
                db.add(alert)
                existing_alerts[key] = alert
                alerts_generated_count += 1
        elif existing_alert:
            # If pollution dropped below threshold on update, remove previous alert
            db.delete(existing_alert)
            del existing_alerts[key]

    db.commit()

    corrupted_count = total_rows - valid_count

    logger.info(
        "Ingestion completed: Total=%d, Valid=%d, Corrupted=%d, Alerts=%d",
        total_rows,
        valid_count,
        corrupted_count,
        alerts_generated_count,
    )

    return IngestionResult(
        total_rows=total_rows,
        valid_rows=valid_count,
        corrupted_rows=corrupted_count,
        alerts_generated=alerts_generated_count,
    )


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize DataFrame column names to standard lowercase identifiers in a single pass.

    Args:
        df: Input raw DataFrame.

    Returns:
        pd.DataFrame: DataFrame with normalized column names.
    """
    col_mapping = {
        col: COLUMN_MAPPING.get(str(col).strip().lower(), str(col).strip().lower())
        for col in df.columns
    }
    return df.rename(columns=col_mapping)


def _validate_and_parse_row(
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
