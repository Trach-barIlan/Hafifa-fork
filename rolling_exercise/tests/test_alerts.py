"""Tests for alerts router endpoints."""

from fastapi.testclient import TestClient


def test_alerts_generation_on_upload(client: TestClient, sample_corrupted_csv: str):
    """Test that CSV upload with high pollution triggers alert generation count."""
    upload_res = client.post(
        "/air_quality_data",
        files={"file": ("alerts_sample.csv", sample_corrupted_csv.encode("utf-8"), "text/csv")},
    )
    assert upload_res.status_code == 201
    assert upload_res.json()["alerts_generated"] == 1


def test_get_all_alerts(client: TestClient, sample_corrupted_csv: str):
    """Test GET /alerts returns generated alerts."""
    client.post(
        "/air_quality_data",
        files={"file": ("alerts_sample.csv", sample_corrupted_csv.encode("utf-8"), "text/csv")},
    )
    alerts_res = client.get("/alerts")
    assert alerts_res.status_code == 200
    alerts = alerts_res.json()
    assert len(alerts) == 1
    assert alerts[0]["city"] == "Netanya"
    assert "alert_id" in alerts[0]
    assert "record_id" in alerts[0]


def test_get_alerts_by_date(client: TestClient, sample_corrupted_csv: str):
    """Test GET /alerts/by_date returns alerts for matching date and empty list for non-matching."""
    client.post(
        "/air_quality_data",
        files={"file": ("alerts_sample.csv", sample_corrupted_csv.encode("utf-8"), "text/csv")},
    )
    date_alerts = client.get("/alerts/by_date", params={"date": "2024-11-21"})
    assert date_alerts.status_code == 200
    assert len(date_alerts.json()) == 1

    empty_date_alerts = client.get("/alerts/by_date", params={"date": "2020-01-01"})
    assert empty_date_alerts.status_code == 200
    assert len(empty_date_alerts.json()) == 0


def test_get_alerts_by_city(client: TestClient, sample_corrupted_csv: str):
    """Test GET /alerts/by_city returns alerts for matching city."""
    client.post(
        "/air_quality_data",
        files={"file": ("alerts_sample.csv", sample_corrupted_csv.encode("utf-8"), "text/csv")},
    )
    city_alerts = client.get("/alerts/by_city", params={"city": "Netanya"})
    assert city_alerts.status_code == 200
    assert len(city_alerts.json()) == 1
