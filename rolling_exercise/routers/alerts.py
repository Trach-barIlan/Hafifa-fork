"""Endpoints for retrieving high pollution alerts."""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database import get_db
from models import Alert
from schemas import AlertResponse

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get(
    "",
    response_model=list[AlertResponse],
    summary="Retrieve all alerts (with optional date and city filters)",
)
def get_all_alerts(
    alert_date: Optional[date] = Query(None, alias="date", description="Filter by date (YYYY-MM-DD)"),
    city: Optional[str] = Query(None, description="Filter by city name"),
    db: Session = Depends(get_db),
) -> list[Alert]:
    """Retrieve all high-pollution alerts, optionally filtered by date and/or city."""
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
    stmt = select(Alert).where(Alert.date == alert_date).order_by(Alert.city.asc())
    alerts = db.scalars(stmt).all()
    return list(alerts)


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
    stmt = (
        select(Alert)
        .where(func.lower(Alert.city) == city.strip().lower())
        .order_by(Alert.date.desc())
    )
    alerts = db.scalars(stmt).all()
    return list(alerts)
