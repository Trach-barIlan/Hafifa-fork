"""Unit tests for CSV ingestion and row validation."""

from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import AirQualityRecord, Alert
from services.csv_service import process_air_quality_csv


def test_process_valid_csv(db_session: Session, sample_valid_csv: str):
    """Test ingestion of cleanly formatted CSV rows."""
    result = process_air_quality_csv(sample_valid_csv, db_session)

    assert result.total_rows == 3
    assert result.valid_rows == 3
    assert result.corrupted_rows == 0

    records = db_session.query(AirQualityRecord).all()
    assert len(records) == 3
    cities = {r.city for r in records}
    assert cities == {"Haifa", "Tel Aviv", "Jerusalem"}


def test_process_corrupted_csv(db_session: Session, sample_corrupted_csv: str):
    """Test that missing or corrupted rows are logged and skipped, while valid rows are saved."""
    result = process_air_quality_csv(sample_corrupted_csv, db_session)

    # 7 rows total: 2 valid (Haifa, Netanya) and 5 corrupted
    assert result.total_rows == 7
    assert result.valid_rows == 2
    assert result.corrupted_rows == 5
    assert result.alerts_generated == 1  # Netanya has high pollutants

    records = db_session.query(AirQualityRecord).all()
    assert len(records) == 2
    assert {r.city for r in records} == {"Haifa", "Netanya"}

    alerts = db_session.query(Alert).all()
    assert len(alerts) == 1
    assert alerts[0].city == "Netanya"
    assert alerts[0].aqi > 300


def test_missing_required_columns(db_session: Session):
    """Test ValueError is raised when required columns are absent."""
    invalid_csv = "date,city,PM2.5\n2024-11-20,Haifa,15.0\n"

    with pytest.raises(ValueError, match="CSV is missing required columns"):
        process_air_quality_csv(invalid_csv, db_session)


def test_duplicate_reupload_upsert(db_session: Session, sample_valid_csv: str):
    """Test re-uploading the same CSV updates records without duplicate key errors."""
    res1 = process_air_quality_csv(sample_valid_csv, db_session)
    assert res1.valid_rows == 3

    # Uploading the exact same data again should succeed and not create duplicate records
    res2 = process_air_quality_csv(sample_valid_csv, db_session)
    assert res2.valid_rows == 3

    total_records = db_session.query(AirQualityRecord).count()
    assert total_records == 3  # No duplicates created


def test_alert_has_record_foreign_key(db_session: Session, sample_corrupted_csv: str):
    """Test alert properly links to parent AirQualityRecord via foreign key."""
    process_air_quality_csv(sample_corrupted_csv, db_session)
    alert = db_session.query(Alert).first()
    assert alert is not None
    assert alert.record_id is not None
    assert alert.record is not None
    assert alert.record.city == alert.city


def test_alert_threshold_boundary(db_session: Session):
    """Verify that AQI <= 300 does not trigger an alert, but AQI > 300 does."""
    # Row 1: PM25=250.4, NO2=53.0, CO2=5.0 -> sub-indices <= 300
    # Row 2: PM25=250.5, NO2=53.0, CO2=5.0 -> PM25 enters 301-500 bracket -> AQI > 300
    csv_content = (
        "date,city,PM2.5,NO2,CO2\n"
        "2024-11-20,CityBelow,250.4,53.0,5.0\n"
        "2024-11-20,CityAbove,250.6,53.0,5.0\n"
    )
    result = process_air_quality_csv(csv_content, db_session)
    assert result.valid_rows == 2
    assert result.alerts_generated == 1

    alerts = db_session.query(Alert).all()
    assert len(alerts) == 1
    assert alerts[0].city == "CityAbove"
    assert alerts[0].aqi > 300


def test_alert_unique_constraint(db_session: Session):
    """Verify that Alert table enforces UniqueConstraint on (city, date)."""
    alert1 = Alert(
        city="Haifa",
        date=date(2024, 11, 20),
        aqi=350.0,
    )
    db_session.add(alert1)
    db_session.commit()

    alert2 = Alert(
        city="Haifa",
        date=date(2024, 11, 20),
        aqi=400.0,
    )
    db_session.add(alert2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

