"""SQLAlchemy ORM models for air quality measurements and alerts."""

from datetime import date
from sqlalchemy import Date, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

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

    __table_args__ = (
        Index("idx_records_city_date", "city", "date"),
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
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    aqi: Mapped[float] = mapped_column(Float, nullable=False)

    def __repr__(self) -> str:
        return f"<Alert(id={self.id}, city='{self.city}', date={self.date}, aqi={self.aqi:.1f})>"
