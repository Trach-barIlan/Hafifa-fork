"""Service layer for alert querying and business logic."""

from datetime import date
from sqlalchemy.orm import Session

from logging_config import logger
from models import Alert
from repositories.alert_repository import AlertRepository


class AlertService:
    """Orchestrates business logic for alert querying."""

    def __init__(self, db: Session):
        self.repository = AlertRepository(db)

    def get_alerts(
        self,
        alert_date: date | None = None,
        city: str | None = None,
    ) -> list[Alert]:
        """Retrieve alerts with optional date and city filters."""
        logger.info(f"Retrieving all alerts: alert_date={alert_date}, city={city}")
        return self.repository.get_alerts(alert_date=alert_date, city=city)

    def get_alerts_by_date(self, alert_date: date) -> list[Alert]:
        """Retrieve alerts registered for a specific date."""
        logger.info(f"Retrieving alerts for date: {alert_date}")
        return self.get_alerts(alert_date=alert_date, city=None)

    def get_alerts_by_city(self, city: str) -> list[Alert]:
        """Retrieve alerts registered for a specific city."""
        logger.info(f"Retrieving alerts for city: {city}")
        return self.get_alerts(alert_date=None, city=city)
