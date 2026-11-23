"""SQLAlchemy ORM models for air quality measurements and alerts."""

from __future__ import annotations

from datetime import date
from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class AirQualityRecord(Base):
    """Represents a validated air quality measurement and its calculated AQI."""

    __tablename__ = "air_quality_records"

    record_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(index=True)
    city: Mapped[str] = mapped_column(String(100), index=True)
    pm25: Mapped[float] = mapped_column()
    no2: Mapped[float] = mapped_column()
    co2: Mapped[float] = mapped_column()
    aqi: Mapped[float] = mapped_column(index=True)
    aqi_level: Mapped[str] = mapped_column(String(50))

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
            f"<AirQualityRecord(record_id={self.record_id}, city='{self.city}', "
            f"date={self.date}, aqi={self.aqi:.1f}, level='{self.aqi_level}')>"
        )


class Alert(Base):
    """Represents a high-pollution alert triggered when AQI exceeds 300."""

    __tablename__ = "alerts"

    alert_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    record_id: Mapped[int] = mapped_column(
        ForeignKey("air_quality_records.record_id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )

    record: Mapped[AirQualityRecord] = relationship(
        "AirQualityRecord",
        back_populates="alerts",
        lazy="joined",
    )

    @property
    def date(self) -> date | None:
        return self.record.date if self.record else None

    @property
    def city(self) -> str | None:
        return self.record.city if self.record else None

    @property
    def aqi(self) -> float | None:
        return self.record.aqi if self.record else None

    def __repr__(self) -> str:
        aqi_str = f"{self.aqi:.1f}" if self.aqi is not None else "None"
        return (
            f"<Alert(alert_id={self.alert_id}, record_id={self.record_id}, "
            f"city='{self.city}', date={self.date}, aqi={aqi_str})>"
        )
