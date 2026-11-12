"""Endpoints for retrieving high pollution alerts."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database import get_db
from logging_config import logger
from models import Alert
from schemas import AlertResponse

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get(
    "",
    response_model=list[AlertResponse],
    summary="Retrieve all alerts (with optional date and city filters)",
)
def get_all_alerts(
    alert_date: date | None = Query(None, alias="date", description="Filter by date (YYYY-MM-DD)"),
    city: str | None = Query(None, description="Filter by city name"),
    db: Session = Depends(get_db),
) -> list[Alert]:
    """Retrieve all high-pollution alerts, optionally filtered by date and/or city."""
    logger.info("Retrieving all alerts: alert_date=%s, city=%s", alert_date, city)
    stmt = select(Alert)

    if alert_date:
        stmt = stmt.where(Alert.date == alert_date)
    if city:
        stmt = stmt.where(func.lower(Alert.city) == city.strip().lower())

    stmt = stmt.order_by(Alert.date.desc(), Alert.id.desc())
    alerts = db.scalars(stmt).all()
    return list(alerts)


@router.get(
    "/by_date",
    response_model=list[AlertResponse],
    summary="Retrieve all alerts from a specific date",
)
def get_alerts_by_date(
    alert_date: date = Query(..., alias="date", description="Target date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
) -> list[Alert]:
    """Retrieve all alerts registered for a specific date."""
    logger.info("Retrieving alerts for date: %s", alert_date)
    return get_all_alerts(alert_date=alert_date, city=None, db=db)


@router.get(
    "/by_city",
    response_model=list[AlertResponse],
    summary="Retrieve all alerts for a specific city",
)
def get_alerts_by_city(
    city: str = Query(..., min_length=1, description="Target city name"),
    db: Session = Depends(get_db),
) -> list[Alert]:
    """Retrieve all alerts registered for a specific city."""
    logger.info("Retrieving alerts for city: %s", city)
    return get_all_alerts(alert_date=None, city=city, db=db)
