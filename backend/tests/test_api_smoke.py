import pytest


def test_root_is_alive(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "RailVision API is running"}


def test_openapi_is_available(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    payload = response.json()
    assert "paths" in payload
    assert "/departures/live/{stop_id}" in payload["paths"]


def test_live_departures_returns_rail_only(client, monkeypatch):
    """live endpoint delegates to _query_departures with rail_only=True."""
    import main

    captured = {}

    def mock_query(stop_id, rail_only=False):
        captured["stop_id"] = stop_id
        captured["rail_only"] = rail_only
        return [
            {"line": "T1", "lineName": None, "destination": None, "operator": None,
             "platform": None, "scheduled_dt": "2026-03-27T01:00:00+00:00",
             "estimated_dt": None, "delay_min": None, "realtime": None},
        ]

    monkeypatch.setattr(main, "_query_departures", mock_query)

    response = client.get("/departures/live/200060")
    assert response.status_code == 200
    assert captured["stop_id"] == "200060"
    assert captured["rail_only"] is True


def test_live_departures_returns_empty_list_when_no_data(client, monkeypatch):
    """live endpoint returns an empty list (not an error) when the DB has no rows."""
    import main

    monkeypatch.setattr(main, "_query_departures", lambda _stop_id, rail_only=False: [])

    response = client.get("/departures/live/200060")
    assert response.status_code == 200
    assert response.json() == []
