import pytest

import services


class FakeResponse:
    def __init__(self, status_code, text="", payload=None):
        self.status_code = status_code
        self.text = text
        self._payload = payload or {}

    def json(self):
        return self._payload


def test_get_departures_non_200_returns_error_dict(monkeypatch):
    def fake_get(*_args, **_kwargs):
        return FakeResponse(status_code=503, text="service unavailable")

    monkeypatch.setattr(services.requests, "get", fake_get)
    result = services.get_departures("200060")

    assert isinstance(result, dict)
    assert "error" in result


def test_get_departures_empty_events_returns_empty_list(monkeypatch):
    def fake_get(*_args, **_kwargs):
        return FakeResponse(status_code=200, payload={"stopEvents": []})

    monkeypatch.setattr(services.requests, "get", fake_get)
    result = services.get_departures("200060")

    assert result == []
