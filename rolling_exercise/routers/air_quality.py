"""Endpoints for air quality measurements, ingestion, and analytics."""

from datetime import date

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.orm import Session

from database import get_db
from logging_config import logger
from models import AirQualityRecord
from schemas import (
    AirQualityRecordResponse,
    BestCityItem,
    CityAverageResponse,
    CityHistoryResponse,
    UploadResponse,
)
from services.air_quality_service import AirQualityService
from services.csv_service import process_air_quality_csv

router = APIRouter(tags=["Air Quality"])


def get_air_quality_service(db: Session = Depends(get_db)) -> AirQualityService:
    """Dependency provider for AirQualityService."""
    return AirQualityService(db)


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
        logger.error(f"Rejected non-CSV upload attempt: {file.filename}")
        raise ValueError("Invalid file format. Please upload a valid .csv file.")

    logger.info(f"Processing upload request for file: {file.filename}")
    content = file.file.read()
    if not content:
        raise ValueError("The uploaded file is empty.")

    result = process_air_quality_csv(content, db)
    return UploadResponse(
        message="File processed successfully.",
        total_rows=result.total_rows,
        valid_rows=result.valid_rows,
        corrupted_rows=result.corrupted_rows,
        alerts_generated=result.alerts_generated,
    )


@router.get(
    "/air_quality_data",
    response_model=list[AirQualityRecordResponse],
    summary="Retrieve air quality data for a date range",
)
def get_air_quality_data(
    start_date: date | None = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: date | None = Query(None, description="End date (YYYY-MM-DD)"),
    service: AirQualityService = Depends(get_air_quality_service),
) -> list[AirQualityRecord]:
    """Retrieve air quality data within an optional date range."""
    return service.get_records_by_range(start_date=start_date, end_date=end_date)


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
    service: AirQualityService = Depends(get_air_quality_service),
) -> list[AirQualityRecord]:
    """Retrieve all air quality records for a specific city."""
    return service.get_records_by_city(city)


@router.get(
    "/city_aqi_history",
    response_model=CityHistoryResponse,
    summary="Retrieve the AQI history for a specific city",
)
def get_city_aqi_history(
    city: str = Query(..., min_length=1, description="City name"),
    service: AirQualityService = Depends(get_air_quality_service),
) -> CityHistoryResponse:
    """Retrieve historical AQI timeline for a specific city."""
    return service.get_city_history(city)


@router.get(
    "/city_aqi_average",
    response_model=CityAverageResponse,
    summary="Retrieve average AQI for a specific city",
)
def get_city_aqi_average(
    city: str = Query(..., min_length=1, description="City name"),
    service: AirQualityService = Depends(get_air_quality_service),
) -> CityAverageResponse:
    """Calculate and return the average AQI value for a specific city."""
    return service.get_city_average(city)


@router.get(
    "/best_cities",
    response_model=list[BestCityItem],
    summary="Retrieve top 3 cities with the best (lowest) AQI based on their most recent reading",
)
def get_best_cities(
    service: AirQualityService = Depends(get_air_quality_service),
) -> list[BestCityItem]:
    """Retrieve 3 cities with the best air quality based on their most recent reading."""
    return service.get_best_cities()
