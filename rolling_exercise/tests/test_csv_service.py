"""Unit tests for CSV ingestion and row validation."""

import pytest
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
