"""Endpoints for retrieving high pollution alerts."""

from datetime import date

from fastapi import APIRouter, Depends, Query

from database import get_db
from models import Alert
from schemas import AlertResponse
from services.alert_service import AlertService

router = APIRouter(prefix="/alerts", tags=["Alerts"])


def get_alert_service(db=Depends(get_db)) -> AlertService:
    """Dependency provider for AlertService."""
    return AlertService(db)


@router.get(
    "",
    response_model=list[AlertResponse],
    summary="Retrieve all alerts (with optional date and city filters)",
)
def get_all_alerts(
    alert_date: date | None = Query(None, alias="date", description="Filter by date (YYYY-MM-DD)"),
    city: str | None = Query(None, description="Filter by city name"),
    service: AlertService = Depends(get_alert_service),
) -> list[Alert]:
    """Retrieve all high-pollution alerts, optionally filtered by date and/or city."""
    return service.get_alerts(alert_date=alert_date, city=city)


@router.get(
    "/by_date",
    response_model=list[AlertResponse],
    summary="Retrieve all alerts from a specific date",
)
def get_alerts_by_date(
    alert_date: date = Query(..., alias="date", description="Target date (YYYY-MM-DD)"),
    service: AlertService = Depends(get_alert_service),
) -> list[Alert]:
    """Retrieve all alerts registered for a specific date."""
    return service.get_alerts_by_date(alert_date)


@router.get(
    "/by_city",
    response_model=list[AlertResponse],
    summary="Retrieve all alerts for a specific city",
)
def get_alerts_by_city(
    city: str = Query(..., min_length=1, description="Target city name"),
    service: AlertService = Depends(get_alert_service),
) -> list[Alert]:
    """Retrieve all alerts registered for a specific city."""
    return service.get_alerts_by_city(city)
