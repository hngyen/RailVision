import pytest

import services
from exceptions import UpstreamUnavailableError


class FakeResponse:
    def __init__(self, status_code, text="", payload=None):
        self.status_code = status_code
        self.text = text
        self._payload = payload or {}

    def json(self):
        return self._payload


@pytest.mark.asyncio
async def test_get_departures_non_200_raises_upstream_error(monkeypatch):
    async def fake_fetch(*_args, **_kwargs):
        return FakeResponse(status_code=503, text="service unavailable")

    monkeypatch.setattr(services, "_fetch_tfnsw", fake_fetch)

    with pytest.raises(UpstreamUnavailableError) as exc_info:
        await services.get_departures("200060")

    assert "service unavailable" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_departures_empty_events_returns_empty_list(monkeypatch):
    async def fake_fetch(*_args, **_kwargs):
        return FakeResponse(status_code=200, payload={"stopEvents": []})

    monkeypatch.setattr(services, "_fetch_tfnsw", fake_fetch)
    result = await services.get_departures("200060")

    assert result == []
