"""Integration tests for all FastAPI endpoints."""

from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    """Test health check route."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "Air Quality API"}


def test_upload_non_csv(client: TestClient):
    """Test uploading a file that is not .csv is rejected."""
    response = client.post(
        "/air_quality_data",
        files={"file": ("data.txt", b"some text", "text/plain")},
    )
    assert response.status_code == 400
    assert "Invalid file format" in response.json()["detail"]


def test_upload_empty_file(client: TestClient):
    """Test uploading an empty CSV file is rejected."""
    response = client.post(
        "/air_quality_data",
        files={"file": ("empty.csv", b"", "text/csv")},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"]


def test_full_api_workflow(client: TestClient, sample_valid_csv: str):
    """Test upload, filtering, aggregation, and querying workflow."""
    # 1. Upload CSV
    upload_res = client.post(
        "/air_quality_data",
        files={"file": ("measurements.csv", sample_valid_csv.encode("utf-8"), "text/csv")},
    )
    assert upload_res.status_code == 201
    data = upload_res.json()
    assert data["total_rows"] == 3
    assert data["valid_rows"] == 3

    # 2. GET all air quality data
    get_res = client.get("/air_quality_data")
    assert get_res.status_code == 200
    assert len(get_res.json()) == 3

    # 3. GET air quality data with date filter
    filtered_res = client.get(
        "/air_quality_data",
        params={"start_date": "2024-11-20", "end_date": "2024-11-20"},
    )
    assert filtered_res.status_code == 200
    assert len(filtered_res.json()) == 3

    out_of_range_res = client.get(
        "/air_quality_data",
        params={"start_date": "2025-01-01", "end_date": "2025-01-02"},
    )
    assert out_of_range_res.status_code == 200
    assert len(out_of_range_res.json()) == 0

    # 4. GET air quality data by city
    city_res = client.get("/air_quality_data/city", params={"city": "Haifa"})
    assert city_res.status_code == 200
    assert len(city_res.json()) == 1
    assert city_res.json()[0]["city"] == "Haifa"

    not_found_res = client.get("/air_quality_data/city", params={"city": "Atlantis"})
    assert not_found_res.status_code == 404

    # 5. GET city AQI history
    history_res = client.get("/city_aqi_history", params={"city": "Haifa"})
    assert history_res.status_code == 200
    history_json = history_res.json()
    assert history_json["city"] == "Haifa"
    assert len(history_json["history"]) == 1

    # 6. GET city AQI average
    avg_res = client.get("/city_aqi_average", params={"city": "Haifa"})
    assert avg_res.status_code == 200
    avg_json = avg_res.json()
    assert avg_json["city"] == "Haifa"
    assert avg_json["reading_count"] == 1
    assert isinstance(avg_json["average_aqi"], float)

    # 7. GET best cities (lowest 3 AQI)
    best_res = client.get("/best_cities")
    assert best_res.status_code == 200
    best_cities = best_res.json()
    assert len(best_cities) == 3
    # Check that best cities are sorted ascending by AQI
    aqi_values = [c["aqi"] for c in best_cities]
    assert aqi_values == sorted(aqi_values)


def test_alerts_endpoints(client: TestClient, sample_corrupted_csv: str):
    """Test alert generation and alert retrieval endpoints."""
    # Upload CSV that triggers an alert for Netanya (AQI > 300)
    upload_res = client.post(
        "/air_quality_data",
        files={"file": ("alerts_sample.csv", sample_corrupted_csv.encode("utf-8"), "text/csv")},
    )
    assert upload_res.status_code == 201
    assert upload_res.json()["alerts_generated"] == 1

    # GET /alerts
    alerts_res = client.get("/alerts")
    assert alerts_res.status_code == 200
    alerts = alerts_res.json()
    assert len(alerts) == 1
    assert alerts[0]["city"] == "Netanya"

    # GET /alerts/by_date
    date_alerts = client.get("/alerts/by_date", params={"date": "2024-11-21"})
    assert date_alerts.status_code == 200
    assert len(date_alerts.json()) == 1

    empty_date_alerts = client.get("/alerts/by_date", params={"date": "2020-01-01"})
    assert empty_date_alerts.status_code == 200
    assert len(empty_date_alerts.json()) == 0

    # GET /alerts/by_city
    city_alerts = client.get("/alerts/by_city", params={"city": "Netanya"})
    assert city_alerts.status_code == 200
    assert len(city_alerts.json()) == 1
