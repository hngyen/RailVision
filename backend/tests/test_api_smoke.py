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


def test_live_departures_filters_non_rail_lines(client, monkeypatch):
    import main

    mock_departures = [
        {"line": "T1", "scheduled_dt": "2026-03-25T01:00:00+00:00"},
        {"line": "M1", "scheduled_dt": "2026-03-25T00:30:00+00:00"},
        {"line": "T80", "scheduled_dt": "2026-03-25T00:45:00+00:00"},
    ]
    monkeypatch.setattr(main, "get_departures", lambda _stop_id: mock_departures)

    response = client.get("/departures/live/200060")
    assert response.status_code == 200

    payload = response.json()
    assert [row["line"] for row in payload] == ["M1", "T1"]


@pytest.mark.xfail(
    reason="Known bug: /departures/live crashes when get_departures returns an error dict.",
    strict=False,
)
def test_live_departures_handles_upstream_error_shape(client, monkeypatch):
    import main

    monkeypatch.setattr(main, "get_departures", lambda _stop_id: {"error": "timeout"})
    response = client.get("/departures/live/200060")

    # Target behavior after refactor: return a typed API error instead of 500 crash.
    assert response.status_code == 502
