"""Repository for database operations on Alert entities."""

from datetime import date
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models import AirQualityRecord, Alert


class AlertRepository:
    """Encapsulates data access and queries for Alert."""

    def __init__(self, db: Session):
        self.db = db

    def get_alerts(
        self,
        alert_date: date | None = None,
        city: str | None = None,
    ) -> list[Alert]:
        """Query alerts with optional date and city filters, ordered by date and alert_id descending."""
        stmt = select(Alert).join(AirQualityRecord)
        if alert_date:
            stmt = stmt.where(AirQualityRecord.date == alert_date)
        if city:
            stmt = stmt.where(func.lower(AirQualityRecord.city) == city.strip().lower())
        stmt = stmt.order_by(AirQualityRecord.date.desc(), Alert.alert_id.desc())
        return list(self.db.scalars(stmt).all())
