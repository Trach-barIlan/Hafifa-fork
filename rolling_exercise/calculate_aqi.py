"""Calculation logic for the Air Quality Index (AQI)."""

from collections.abc import Sequence

from constants import (
    AQI_THRESHOLDS,
    CO2_BREAKPOINTS,
    MAX_AQI,
    NO2_BREAKPOINTS,
    PM25_BREAKPOINTS,
)


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

    overall_aqi = max(min(pm25_aqi, MAX_AQI), 0, min(no2_aqi, MAX_AQI), 0, min(co2_aqi, MAX_AQI), 0)

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
    return MAX_AQI
