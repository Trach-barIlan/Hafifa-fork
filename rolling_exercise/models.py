"""SQLAlchemy ORM models for air quality measurements and alerts."""

from __future__ import annotations

from datetime import date
from sqlalchemy import Date, Float, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class AirQualityRecord(Base):
    """Represents a validated air quality measurement and its calculated AQI."""

    __tablename__ = "air_quality_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    pm25: Mapped[float] = mapped_column(Float, nullable=False)
    no2: Mapped[float] = mapped_column(Float, nullable=False)
    co2: Mapped[float] = mapped_column(Float, nullable=False)
    aqi: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    aqi_level: Mapped[str] = mapped_column(String(50), nullable=False)

    alerts: Mapped[list[Alert]] = relationship(
        "Alert",
        back_populates="record",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_records_city_date", "city", "date"),
        UniqueConstraint("city", "date", name="uq_city_date"),
    )

    def __repr__(self) -> str:
        return (
            f"<AirQualityRecord(id={self.id}, city='{self.city}', "
            f"date={self.date}, aqi={self.aqi:.1f}, level='{self.aqi_level}')>"
        )


class Alert(Base):
    """Represents a high-pollution alert triggered when AQI exceeds 300."""

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    record_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("air_quality_records.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    aqi: Mapped[float] = mapped_column(Float, nullable=False)

    record: Mapped[AirQualityRecord | None] = relationship(
        "AirQualityRecord",
        back_populates="alerts",
    )

    __table_args__ = (
        Index("idx_alerts_city_date", "city", "date"),
        UniqueConstraint("city", "date", name="uq_alert_city_date"),
    )

    def __repr__(self) -> str:
        return (
            f"<Alert(id={self.id}, record_id={self.record_id}, "
            f"city='{self.city}', date={self.date}, aqi={self.aqi:.1f})>"
        )
