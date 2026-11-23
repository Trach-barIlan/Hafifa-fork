"""Tests for air quality router endpoints and root health check."""

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


def test_upload_valid_csv(client: TestClient, sample_valid_csv: str):
    """Test uploading valid CSV data."""
    upload_res = client.post(
        "/air_quality_data",
        files={"file": ("measurements.csv", sample_valid_csv.encode("utf-8"), "text/csv")},
    )
    assert upload_res.status_code == 201
    data = upload_res.json()
    assert data["total_rows"] == 3
    assert data["valid_rows"] == 3


def test_get_all_air_quality_data(client: TestClient, sample_valid_csv: str):
    """Test GET all air quality data after uploading."""
    client.post(
        "/air_quality_data",
        files={"file": ("measurements.csv", sample_valid_csv.encode("utf-8"), "text/csv")},
    )
    get_res = client.get("/air_quality_data")
    assert get_res.status_code == 200
    records_json = get_res.json()
    assert len(records_json) == 3
    assert "record_id" in records_json[0]


def test_get_air_quality_data_date_filter(client: TestClient, sample_valid_csv: str):
    """Test GET air quality data with date filters (matching and out-of-range)."""
    client.post(
        "/air_quality_data",
        files={"file": ("measurements.csv", sample_valid_csv.encode("utf-8"), "text/csv")},
    )
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


def test_get_air_quality_data_by_city(client: TestClient, sample_valid_csv: str):
    """Test GET air quality data by city name (existing and non-existing)."""
    client.post(
        "/air_quality_data",
        files={"file": ("measurements.csv", sample_valid_csv.encode("utf-8"), "text/csv")},
    )
    city_res = client.get("/air_quality_data/city", params={"city": "Haifa"})
    assert city_res.status_code == 200
    assert len(city_res.json()) == 1
    assert city_res.json()[0]["city"] == "Haifa"

    empty_city_res = client.get("/air_quality_data/city", params={"city": "Atlantis"})
    assert empty_city_res.status_code == 200
    assert empty_city_res.json() == []


def test_inverted_date_range(client: TestClient):
    """Test passing start_date > end_date returns 400."""
    res = client.get(
        "/air_quality_data",
        params={"start_date": "2024-11-25", "end_date": "2024-11-20"},
    )
    assert res.status_code == 400
    assert "start_date cannot be later than end_date" in res.json()["detail"]


def test_get_city_aqi_history(client: TestClient, sample_valid_csv: str):
    """Test GET city AQI history for existing and non-existing cities."""
    client.post(
        "/air_quality_data",
        files={"file": ("measurements.csv", sample_valid_csv.encode("utf-8"), "text/csv")},
    )
    history_res = client.get("/city_aqi_history", params={"city": "Haifa"})
    assert history_res.status_code == 200
    history_json = history_res.json()
    assert history_json["city"] == "Haifa"
    assert len(history_json["history"]) == 1

    empty_history_res = client.get("/city_aqi_history", params={"city": "Atlantis"})
    assert empty_history_res.status_code == 200
    assert empty_history_res.json()["history"] == []


def test_get_city_aqi_average(client: TestClient, sample_valid_csv: str):
    """Test GET city AQI average for existing and non-existing cities."""
    client.post(
        "/air_quality_data",
        files={"file": ("measurements.csv", sample_valid_csv.encode("utf-8"), "text/csv")},
    )
    avg_res = client.get("/city_aqi_average", params={"city": "Haifa"})
    assert avg_res.status_code == 200
    avg_json = avg_res.json()
    assert avg_json["city"] == "Haifa"
    assert avg_json["reading_count"] == 1
    assert isinstance(avg_json["average_aqi"], float)

    avg_not_found = client.get("/city_aqi_average", params={"city": "Atlantis"})
    assert avg_not_found.status_code == 404


def test_get_best_cities(client: TestClient, sample_valid_csv: str):
    """Test GET best cities (lowest 3 AQI)."""
    client.post(
        "/air_quality_data",
        files={"file": ("measurements.csv", sample_valid_csv.encode("utf-8"), "text/csv")},
    )
    best_res = client.get("/best_cities")
    assert best_res.status_code == 200
    best_cities = best_res.json()
    assert len(best_cities) == 3
    # Check that best cities are sorted ascending by AQI
    aqi_values = [c["aqi"] for c in best_cities]
    assert aqi_values == sorted(aqi_values)


def test_best_cities_returns_distinct_cities(client: TestClient):
    """Test best cities returns distinct cities even if one city has multiple top readings."""
    csv_data = (
        "date,city,PM2.5,NO2,CO2\n"
        "2024-11-20,CityA,5.0,10.0,2.0\n"
        "2024-11-21,CityA,6.0,11.0,2.0\n"
        "2024-11-22,CityA,7.0,12.0,2.0\n"
        "2024-11-20,CityB,15.0,20.0,4.0\n"
        "2024-11-20,CityC,25.0,30.0,6.0\n"
    )
    client.post(
        "/air_quality_data",
        files={"file": ("cities.csv", csv_data.encode("utf-8"), "text/csv")},
    )
    res = client.get("/best_cities")
    assert res.status_code == 200
    data = res.json()
    cities = [item["city"] for item in data]
    assert len(cities) == len(set(cities))
    assert set(cities) == {"CityA", "CityB", "CityC"}

    # Verify that CityA's reading is its MOST RECENT date (2024-11-22)
    city_a_record = next(item for item in data if item["city"] == "CityA")
    assert city_a_record["date"] == "2024-11-22"
