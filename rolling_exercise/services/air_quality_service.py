"""Service layer for air quality business logic."""

from datetime import date
from sqlalchemy.orm import Session

from logging_config import logger
from models import AirQualityRecord
from repositories.air_quality_repository import AirQualityRepository
from schemas import (
    BestCityItem,
    CityAverageResponse,
    CityHistoryItem,
    CityHistoryResponse,
)


class AirQualityService:
    """Orchestrates business logic for air quality records and analytics."""

    def __init__(self, db: Session):
        self.repository = AirQualityRepository(db)

    def get_records_by_range(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[AirQualityRecord]:
        """Validate date range and retrieve records."""
        logger.info(f"Retrieving air quality data for range: start_date={start_date}, end_date={end_date}")
        if start_date and end_date and start_date > end_date:
            raise ValueError("start_date cannot be later than end_date.")
        return self.repository.get_by_date_range(start_date=start_date, end_date=end_date)

    def get_records_by_city(self, city: str) -> list[AirQualityRecord]:
        """Retrieve all records for a specific city."""
        logger.info(f"Retrieving air quality records for city: {city}")
        records = self.repository.get_by_city(city)
        if not records:
            logger.info(f"No records found for city '{city}'")
        return records

    def get_city_history(self, city: str) -> CityHistoryResponse:
        """Retrieve historical timeline of AQI values for a city."""
        logger.info(f"Retrieving AQI history for city: {city}")
        records = self.repository.get_city_history(city)
        if not records:
            logger.info(f"No AQI history found for city '{city}'")

        history = [
            CityHistoryItem(date=rec.date, aqi=rec.aqi, aqi_level=rec.aqi_level)
            for rec in records
        ]
        city_name = records[0].city if records else city.strip()
        return CityHistoryResponse(city=city_name, history=history)

    def get_city_average(self, city: str) -> CityAverageResponse:
        """Calculate and return average AQI for a city."""
        logger.info(f"Calculating AQI average for city: {city}")
        avg_aqi, count = self.repository.get_city_average(city)
        if avg_aqi is None or count == 0:
            raise LookupError(f"No records found to calculate average for city '{city}'.")

        return CityAverageResponse(
            city=city.strip(),
            average_aqi=round(avg_aqi, 2),
            reading_count=count,
        )

    def get_best_cities(self) -> list[BestCityItem]:
        """Retrieve top cities with lowest AQI based on most recent reading."""
        logger.info("Retrieving top 3 cities with the best AQI based on most recent reading")
        records = self.repository.get_best_cities()
        return [
            BestCityItem(
                city=rec.city,
                date=rec.date,
                aqi=rec.aqi,
                aqi_level=rec.aqi_level,
            )
            for rec in records
        ]
