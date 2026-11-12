"""Calculation logic for the Air Quality Index (AQI)."""

from collections.abc import Sequence

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


def calculate_aqi(pm25: float, no2: float, co2: float) -> tuple[float, str]:
    """Calculate the overall AQI and category level based on pollutant measurements.

    Args:
        pm25: Fine particulate matter measurement.
        no2: Nitrogen dioxide measurement.
        co2: Carbon dioxide measurement.

    Returns:
        tuple[float, str]: Overall AQI value and descriptive category level.
    """
    pm25_aqi = calculate_sub_index(pm25, PM25_BREAKPOINTS)
    no2_aqi = calculate_sub_index(no2, NO2_BREAKPOINTS)
    co2_aqi = calculate_sub_index(co2, CO2_BREAKPOINTS)

    overall_aqi = max(min(pm25_aqi, 500), 0, min(no2_aqi, 500), 0, min(co2_aqi, 500), 0)

    aqi_level = next(
        (level for threshold, level in AQI_THRESHOLDS if overall_aqi <= threshold),
        "Hazardous",
    )

    return overall_aqi, aqi_level


def calculate_sub_index(
    value: float,
    breakpoints: Sequence[tuple[float, float, int, int]],
) -> float:
    """Calculate the AQI sub-index for a specific pollutant value against breakpoints.

    Args:
        value: Pollutant level measurement.
        breakpoints: Sequence of (lower, upper, aqi_lower, aqi_upper) intervals.

    Returns:
        float: Calculated sub-index AQI value.
    """
    for lower, upper, aqi_lower, aqi_upper in breakpoints:
        if lower <= value <= upper:
            return aqi_lower + (value - lower) * (aqi_upper - aqi_lower) / (upper - lower)
    return 500
