"""Endpoints for air quality measurements, ingestion, and analytics."""

from datetime import date

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database import get_db
from logging_config import logger
from models import AirQualityRecord
from schemas import (
    AirQualityRecordResponse,
    BestCityItem,
    CityAverageResponse,
    CityHistoryItem,
    CityHistoryResponse,
    UploadResponse,
)
from services.csv_service import process_air_quality_csv

router = APIRouter(tags=["Air Quality"])


@router.post(
    "/air_quality_data",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload air quality data from a CSV file",
)
def upload_air_quality_data(
    file: UploadFile = File(..., description="CSV file containing air quality records"),
    db: Session = Depends(get_db),
) -> UploadResponse:
    """Upload air quality CSV data, validate rows, compute AQI, and store in DB."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        logger.error("Rejected non-CSV upload attempt: %s", file.filename)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Please upload a valid .csv file.",
        )

    try:
        content = file.file.read()
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded file is empty.",
            )

        result = process_air_quality_csv(content, db)
        return UploadResponse(
            message="File processed successfully.",
            total_rows=result.total_rows,
            valid_rows=result.valid_rows,
            corrupted_rows=result.corrupted_rows,
            alerts_generated=result.alerts_generated,
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error processing upload: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the CSV file.",
        ) from exc


@router.get(
    "/air_quality_data",
    response_model=list[AirQualityRecordResponse],
    summary="Retrieve air quality data for a date range",
)
def get_air_quality_data(
    start_date: date | None = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: date | None = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
) -> list[AirQualityRecord]:

    """Retrieve air quality data within an optional date range."""
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date cannot be later than end_date.",
        )

    stmt = select(AirQualityRecord)

    if start_date:
        stmt = stmt.where(AirQualityRecord.date >= start_date)
    if end_date:
        stmt = stmt.where(AirQualityRecord.date <= end_date)

    stmt = stmt.order_by(AirQualityRecord.date.asc(), AirQualityRecord.city.asc())
    records = db.scalars(stmt).all()
    return list(records)


@router.get(
    "/air_quality_data/city",
    response_model=list[AirQualityRecordResponse],
    summary="Retrieve air quality data for a specific city",
)
@router.get(
    "/air_quality_data_by_city",
    response_model=list[AirQualityRecordResponse],
    include_in_schema=False,
)
def get_air_quality_data_by_city(
    city: str = Query(..., min_length=1, description="City name"),
    db: Session = Depends(get_db),
) -> list[AirQualityRecord]:
    """Retrieve all air quality records for a specific city."""
    stmt = (
        select(AirQualityRecord)
        .where(func.lower(AirQualityRecord.city) == city.strip().lower())
        .order_by(AirQualityRecord.date.desc())
    )
    records = db.scalars(stmt).all()
    if not records:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No air quality records found for city '{city}'.",
        )
    return list(records)


@router.get(
    "/city_aqi_history",
    response_model=CityHistoryResponse,
    summary="Retrieve the AQI history for a specific city",
)
def get_city_aqi_history(
    city: str = Query(..., min_length=1, description="City name"),
    db: Session = Depends(get_db),
) -> CityHistoryResponse:
    """Retrieve historical AQI timeline for a specific city."""
    stmt = (
        select(AirQualityRecord)
        .where(func.lower(AirQualityRecord.city) == city.strip().lower())
        .order_by(AirQualityRecord.date.asc())
    )
    records = db.scalars(stmt).all()
    if not records:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No AQI history found for city '{city}'.",
        )

    history = [
        CityHistoryItem(date=rec.date, aqi=rec.aqi, aqi_level=rec.aqi_level)
        for rec in records
    ]
    return CityHistoryResponse(city=records[0].city, history=history)


@router.get(
    "/city_aqi_average",
    response_model=CityAverageResponse,
    summary="Retrieve average AQI for a specific city",
)
def get_city_aqi_average(
    city: str = Query(..., min_length=1, description="City name"),
    db: Session = Depends(get_db),
) -> CityAverageResponse:
    """Calculate and return the average AQI value for a specific city."""
    stmt = select(
        func.avg(AirQualityRecord.aqi).label("avg_aqi"),
        func.count(AirQualityRecord.id).label("record_count"),
    ).where(func.lower(AirQualityRecord.city) == city.strip().lower())

    result = db.execute(stmt).one_or_none()

    if not result or result.record_count == 0 or result.avg_aqi is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No records found to calculate average for city '{city}'.",
        )

    return CityAverageResponse(
        city=city.strip(),
        average_aqi=round(float(result.avg_aqi), 2),
        reading_count=int(result.record_count),
    )


@router.get(
    "/best_cities",
    response_model=list[BestCityItem],
    summary="Retrieve top 3 cities with the best (lowest) AQI based on their most recent reading",
)
def get_best_cities(
    db: Session = Depends(get_db),
) -> list[BestCityItem]:
    """Retrieve 3 cities with the best air quality based on their most recent reading."""
    # Subquery to find the most recent date for each city
    subq = (
        select(
            AirQualityRecord.city,
            func.max(AirQualityRecord.date).label("latest_date"),
        )
        .group_by(AirQualityRecord.city)
        .subquery()
    )

    # Join back to get each city's most recent record, ordered by lowest AQI
    stmt = (
        select(AirQualityRecord)
        .join(
            subq,
            (AirQualityRecord.city == subq.c.city)
            & (AirQualityRecord.date == subq.c.latest_date),
        )
        .order_by(AirQualityRecord.aqi.asc(), AirQualityRecord.city.asc())
        .limit(3)
    )

    records = db.scalars(stmt).all()

    return [
        BestCityItem(
            city=rec.city,
            date=rec.date,
            aqi=rec.aqi,
            aqi_level=rec.aqi_level,
        )
        for rec in records
    ]


