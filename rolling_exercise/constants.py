"""Application-wide immutable domain constants and literals."""

# ==============================================================================
# Logging Constants
# ==============================================================================
DEFAULT_LOGGER_NAME = "air_quality_api"
LOG_FORMAT = "%(asctime)s - [%(levelname)s] - %(name)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
LOG_BACKUP_COUNT = 5

# ==============================================================================
# CSV Ingestion & Validation Constants
# ==============================================================================
COLUMN_MAPPING: dict[str, str] = {
    "date": "date",
    "city": "city",
    "pm2.5": "pm25",
    "pm25": "pm25",
    "no2": "no2",
    "co2": "co2",
}

REQUIRED_COLUMNS: set[str] = {"date", "city", "pm25", "no2", "co2"}

# ==============================================================================
# AQI Calculation Breakpoints & Thresholds (EPA Standard)
# ==============================================================================
MAX_AQI: float = 500.0

PM25_BREAKPOINTS: list[tuple[float, float, int, int]] = [
    (0, 12, 0, 50),
    (12.1, 35.4, 51, 100),
    (35.5, 55.4, 101, 150),
    (55.5, 150.4, 151, 200),
    (150.5, 250.4, 201, 300),
    (250.5, 500.4, 301, 500),
]

NO2_BREAKPOINTS: list[tuple[float, float, int, int]] = [
    (0, 53, 0, 50),
    (54, 100, 51, 100),
    (101, 360, 101, 150),
    (361, 649, 151, 200),
    (650, 1249, 201, 300),
    (1250, 2049, 301, 500),
]

CO2_BREAKPOINTS: list[tuple[float, float, int, int]] = [
    (0, 5, 0, 50),
    (5.1, 15, 51, 100),
    (15.1, 30, 101, 150),
    (30.1, 60, 151, 200),
    (60.1, 100, 201, 300),
    (100.1, 200, 301, 500),
]

AQI_THRESHOLDS: list[tuple[int, str]] = [
    (50, "Good"),
    (100, "Moderate"),
    (150, "Unhealthy for Sensitive Groups"),
    (200, "Unhealthy"),
    (300, "Very Unhealthy"),
    (500, "Hazardous"),
]

# ==============================================================================
# API Endpoint Constants
# ==============================================================================
BEST_CITIES_LIMIT: int = 3
