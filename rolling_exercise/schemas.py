"""Pydantic schemas for request validation and response serialization."""

from datetime import date
from pydantic import BaseModel, ConfigDict, Field




class AirQualityRecordResponse(BaseModel):
    """Schema representing an air quality database record."""

    id: int
    date: date
    city: str
    pm25: float
    no2: float
    co2: float
    aqi: float
    aqi_level: str

    model_config = ConfigDict(from_attributes=True)


class AlertResponse(BaseModel):
    """Schema representing a high pollution alert."""

    id: int
    record_id: int | None = None
    date: date
    city: str
    aqi: float

    model_config = ConfigDict(from_attributes=True)




class CityAverageResponse(BaseModel):
    """Schema for the average AQI calculation of a city."""

    city: str
    average_aqi: float = Field(..., description="Average AQI rounded to 2 decimals")
    reading_count: int


class CityHistoryItem(BaseModel):
    """Individual historical AQI entry."""

    date: date
    aqi: float
    aqi_level: str

    model_config = ConfigDict(from_attributes=True)


class CityHistoryResponse(BaseModel):
    """Schema for historical AQI readings of a city."""

    city: str
    history: list[CityHistoryItem]


class BestCityItem(BaseModel):
    """Best city representation by lowest AQI."""

    city: str
    date: date
    aqi: float
    aqi_level: str

    model_config = ConfigDict(from_attributes=True)


class UploadResponse(BaseModel):
    """Schema for CSV upload processing results."""

    message: str
    total_rows: int
    valid_rows: int
    corrupted_rows: int
    alerts_generated: int
