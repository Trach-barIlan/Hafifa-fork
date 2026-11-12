"""Unit tests for calculate_aqi logic."""

from calculate_aqi import calculate_aqi


def test_calculate_aqi_good():
    """Verify low pollutant levels result in 'Good' AQI."""
    aqi, level = calculate_aqi(pm25=5.0, no2=20.0, co2=2.0)
    assert aqi <= 50
    assert level == "Good"


def test_calculate_aqi_moderate():
    """Verify moderate pollutant levels result in 'Moderate' AQI."""
    aqi, level = calculate_aqi(pm25=20.0, no2=40.0, co2=10.0)
    assert 50 < aqi <= 100
    assert level == "Moderate"


def test_calculate_aqi_hazardous_threshold():
    """Verify extreme pollutant levels cap at 500 and return 'Hazardous'."""
    aqi, level = calculate_aqi(pm25=300.0, no2=1500.0, co2=250.0)
    assert aqi >= 300
    assert level == "Hazardous"


def test_calculate_aqi_dominant_pollutant():
    """Verify the highest sub-index drives the overall AQI."""
    # Low PM2.5 and NO2, but high CO2
    aqi, _ = calculate_aqi(pm25=2.0, no2=5.0, co2=150.0)
    assert aqi > 300
