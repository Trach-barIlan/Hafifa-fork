"""Repository for database operations on AirQualityRecord entities."""

from datetime import date
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from constants import BEST_CITIES_LIMIT
from models import AirQualityRecord


class AirQualityRepository:
    """Encapsulates data access and queries for AirQualityRecord."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_date_range(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[AirQualityRecord]:
        """Query air quality records within an optional date range ordered by date and city."""
        stmt = select(AirQualityRecord)
        if start_date:
            stmt = stmt.where(AirQualityRecord.date >= start_date)
        if end_date:
            stmt = stmt.where(AirQualityRecord.date <= end_date)
        stmt = stmt.order_by(AirQualityRecord.date.asc(), AirQualityRecord.city.asc())
        return list(self.db.scalars(stmt).all())

    def get_by_city(self, city: str) -> list[AirQualityRecord]:
        """Query all records for a city case-insensitively, ordered by date descending."""
        stmt = (
            select(AirQualityRecord)
            .where(func.lower(AirQualityRecord.city) == city.strip().lower())
            .order_by(AirQualityRecord.date.desc())
        )
        return list(self.db.scalars(stmt).all())

    def get_city_history(self, city: str) -> list[AirQualityRecord]:
        """Query timeline records for a city ordered by date ascending."""
        stmt = (
            select(AirQualityRecord)
            .where(func.lower(AirQualityRecord.city) == city.strip().lower())
            .order_by(AirQualityRecord.date.asc())
        )
        return list(self.db.scalars(stmt).all())

    def get_city_average(self, city: str) -> tuple[float | None, int]:
        """Query average AQI and total count of records for a city."""
        stmt = select(
            func.avg(AirQualityRecord.aqi).label("avg_aqi"),
            func.count(AirQualityRecord.record_id).label("record_count"),
        ).where(func.lower(AirQualityRecord.city) == city.strip().lower())
        result = self.db.execute(stmt).one_or_none()
        if not result or result.record_count == 0 or result.avg_aqi is None:
            return None, 0
        return float(result.avg_aqi), int(result.record_count)

    def get_best_cities(self, limit: int = BEST_CITIES_LIMIT) -> list[AirQualityRecord]:
        """Query top cities with lowest AQI based on each city's most recent reading."""
        subq = (
            select(
                AirQualityRecord.city,
                func.max(AirQualityRecord.date).label("latest_date"),
            )
            .group_by(AirQualityRecord.city)
            .subquery()
        )
        stmt = (
            select(AirQualityRecord)
            .join(
                subq,
                (AirQualityRecord.city == subq.c.city)
                & (AirQualityRecord.date == subq.c.latest_date),
            )
            .order_by(AirQualityRecord.aqi.asc(), AirQualityRecord.city.asc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())
