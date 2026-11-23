"""Service for reading, validating, and ingesting air quality CSV files."""

from datetime import date
from io import BytesIO, StringIO
from typing import BinaryIO, TextIO

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from calculate_aqi import calculate_aqi
from config import settings
from constants import COLUMN_MAPPING, REQUIRED_COLUMNS
from logging_config import logger
from models import AirQualityRecord, Alert, IngestionResult
from services.row_validator import validate_and_parse_row

ALERT_AQI_THRESHOLD = settings.alert_aqi_threshold

# Backward-compatibility alias
_validate_and_parse_row = validate_and_parse_row


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

    df = _load_and_validate_dataframe(file_content)
    total_rows = len(df)

    rows_data = df.to_dict(orient="records")
    valid_parsed_rows = _parse_valid_rows(rows_data)

    if not valid_parsed_rows:
        return IngestionResult(
            total_rows=total_rows,
            valid_rows=0,
            corrupted_rows=total_rows,
            alerts_generated=0,
        )

    valid_count, alerts_generated_count = _persist_air_quality_records(
        valid_parsed_rows, db
    )

    corrupted_count = total_rows - valid_count
    logger.info(
        f"Ingestion completed: Total={total_rows}, Valid={valid_count}, Corrupted={corrupted_count}, Alerts={alerts_generated_count}"
    )

    return IngestionResult(
        total_rows=total_rows,
        valid_rows=valid_count,
        corrupted_rows=corrupted_count,
        alerts_generated=alerts_generated_count,
    )


def _load_and_validate_dataframe(
    file_content: str | bytes | BinaryIO | TextIO,
) -> pd.DataFrame:
    """Parse CSV content and ensure required columns are present."""
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
        logger.error(f"Failed to parse CSV file: {exc}")
        raise ValueError(f"Could not parse CSV content: {exc}") from exc

    df = _normalize_columns(df)
    missing_columns = REQUIRED_COLUMNS - set(df.columns)
    if missing_columns:
        err_msg = f"CSV is missing required columns: {sorted(missing_columns)}"
        logger.error(err_msg)
        raise ValueError(err_msg)

    return df


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize DataFrame column names to standard lowercase identifiers."""
    col_mapping = {
        col: COLUMN_MAPPING.get(str(col).strip().lower(), str(col).strip().lower())
        for col in df.columns
    }
    return df.rename(columns=col_mapping)


def _parse_valid_rows(
    rows_data: list[dict],
) -> list[tuple[date, str, float, float, float]]:
    """Validate all rows and return only valid parsed tuples."""
    valid_rows: list[tuple[date, str, float, float, float]] = []
    for idx, row in enumerate(rows_data):
        validated_data = validate_and_parse_row(idx, row)
        if validated_data is not None:
            valid_rows.append(validated_data)
    return valid_rows


def _load_existing_entities(
    distinct_dates: set[date],
    db: Session,
) -> tuple[dict[tuple[str, date], AirQualityRecord], dict[tuple[str, date], Alert]]:
    """Batch-load existing records and alerts for given dates."""
    existing_records = {
        (rec.city.lower(), rec.date): rec
        for rec in db.scalars(
            select(AirQualityRecord).where(AirQualityRecord.date.in_(distinct_dates))
        ).all()
    }
    existing_alerts = {
        (alert.city.lower(), alert.date): alert
        for alert in db.scalars(
            select(Alert).join(AirQualityRecord).where(AirQualityRecord.date.in_(distinct_dates))
        ).all()
    }
    return existing_records, existing_alerts


def _upsert_record(
    record_date: date,
    city: str,
    pm25: float,
    no2: float,
    co2: float,
    aqi_value: float,
    aqi_level: str,
    existing_records: dict[tuple[str, date], AirQualityRecord],
    db: Session,
) -> AirQualityRecord:
    """Insert or update an air quality record."""
    key = (city.lower(), record_date)
    existing_record = existing_records.get(key)
    if existing_record:
        existing_record.pm25 = pm25
        existing_record.no2 = no2
        existing_record.co2 = co2
        existing_record.aqi = aqi_value
        existing_record.aqi_level = aqi_level
        logger.info(f"Updated existing record for {city} on {record_date}")
        return existing_record

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
    return target_record


def _sync_alert(
    target_record: AirQualityRecord,
    city: str,
    record_date: date,
    aqi_value: float,
    existing_alerts: dict[tuple[str, date], Alert],
    db: Session,
) -> int:
    """Create, update, or remove an alert based on AQI threshold. Returns 1 if a new alert was created."""
    key = (city.lower(), record_date)
    existing_alert = existing_alerts.get(key)
    alerts_generated = 0

    if aqi_value > ALERT_AQI_THRESHOLD:
        logger.warning(
            f"High pollution alert triggered! City: {city}, Date: {record_date}, AQI: {aqi_value:.1f}"
        )
        if existing_alert:
            existing_alert.record = target_record
        else:
            alert = Alert(record=target_record)
            db.add(alert)
            existing_alerts[key] = alert
            alerts_generated = 1
    elif existing_alert:
        db.delete(existing_alert)
        del existing_alerts[key]

    return alerts_generated


def _persist_air_quality_records(
    valid_rows: list[tuple[date, str, float, float, float]],
    db: Session,
) -> tuple[int, int]:
    """Calculate AQI, upsert records and alerts, and commit to database."""
    distinct_dates = {rec[0] for rec in valid_rows}
    existing_records, existing_alerts = _load_existing_entities(distinct_dates, db)

    valid_count = 0
    alerts_generated_count = 0

    for record_date, city, pm25, no2, co2 in valid_rows:
        valid_count += 1
        aqi_value, aqi_level = calculate_aqi(pm25, no2, co2)
        logger.info(
            f"Calculated AQI for {city} on {record_date}: AQI={aqi_value:.1f} ({aqi_level})"
        )

        target_record = _upsert_record(
            record_date, city, pm25, no2, co2, aqi_value, aqi_level, existing_records, db
        )
        alerts_generated_count += _sync_alert(
            target_record, city, record_date, aqi_value, existing_alerts, db
        )

    db.commit()
    return valid_count, alerts_generated_count
