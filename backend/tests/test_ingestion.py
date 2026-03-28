"""Integration test: proves batch upsert persists ALL rows, not just the last one.

This directly validates the fix for the data-loss bug where the ingestion loop
overwrote a single `record` variable, silently discarding ~97% of fetched departures.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker

import services
import database
from models import Departure, Base


# -- Helpers ------------------------------------------------------------------

def _make_stop_event(line: str, minutes_from_now: int, delay_seconds: int = 0):
    """Build a single TfNSW stopEvent dict."""
    scheduled = datetime.now(timezone.utc) + timedelta(minutes=minutes_from_now)
    estimated = scheduled + timedelta(seconds=delay_seconds)
    return {
        "transportation": {
            "disassembledName": line,
            "number": f"{line} Test Line",
            "destination": {"name": "Test Destination"},
            "operator": {"name": "Sydney Trains"},
        },
        "location": {"properties": {"platformName": "Platform 1"}},
        "departureTimePlanned": scheduled.isoformat(),
        "departureTimeEstimated": estimated.isoformat(),
        "isRealtimeControlled": True,
    }


def _fake_tfnsw_response(stop_events: list) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"stopEvents": stop_events}
    return resp


# -- Fixtures -----------------------------------------------------------------

@pytest.fixture()
def test_db(monkeypatch):
    """Swap in a fresh in-memory SQLite DB for the duration of one test."""
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(test_engine)
    test_session_factory = sessionmaker(bind=test_engine)

    monkeypatch.setattr(database, "engine", test_engine)
    monkeypatch.setattr(database, "SessionLocal", test_session_factory)
    monkeypatch.setattr(services, "engine", test_engine)
    monkeypatch.setattr(services, "SessionLocal", test_session_factory)

    yield test_engine, test_session_factory


# -- Tests --------------------------------------------------------------------

@pytest.mark.asyncio
async def test_batch_upsert_persists_all_rows(monkeypatch, test_db):
    """Every fetched departure must land in the DB — not just the last one."""
    test_engine, Session = test_db

    events = [
        _make_stop_event("T1", 5, delay_seconds=60),
        _make_stop_event("T2", 10, delay_seconds=120),
        _make_stop_event("T3", 15, delay_seconds=0),
        _make_stop_event("T4", 20, delay_seconds=180),
        _make_stop_event("T9", 25, delay_seconds=30),
    ]

    async def fake_fetch(*_args, **_kwargs):
        return _fake_tfnsw_response(events)

    monkeypatch.setattr(services, "_fetch_tfnsw", fake_fetch)

    result = await services.get_departures("200060")

    # API returns all 5
    assert len(result) == 5

    # DB has all 5
    db = Session()
    count = db.query(func.count(Departure.id)).scalar()
    db.close()
    assert count == 5, f"Expected 5 rows in DB, got {count}"


@pytest.mark.asyncio
async def test_upsert_updates_existing_row_on_conflict(monkeypatch, test_db):
    """A second poll with updated delay for the same trip should update, not duplicate."""
    test_engine, Session = test_db

    event = _make_stop_event("T1", 10, delay_seconds=60)

    async def fake_fetch(*_args, **_kwargs):
        return _fake_tfnsw_response([event])

    monkeypatch.setattr(services, "_fetch_tfnsw", fake_fetch)

    # First poll
    await services.get_departures("200060")

    # Second poll — same trip, bigger delay
    event_updated = dict(event)
    scheduled_iso = event["departureTimePlanned"]
    new_estimated = (
        datetime.fromisoformat(scheduled_iso) + timedelta(seconds=300)
    ).isoformat()
    event_updated["departureTimeEstimated"] = new_estimated

    async def fake_fetch_updated(*_args, **_kwargs):
        return _fake_tfnsw_response([event_updated])

    monkeypatch.setattr(services, "_fetch_tfnsw", fake_fetch_updated)

    await services.get_departures("200060")

    # Still 1 row, not 2
    db = Session()
    count = db.query(func.count(Departure.id)).scalar()
    row = db.query(Departure).first()
    db.close()

    assert count == 1, f"Expected 1 row after upsert, got {count}"
    assert row.delay_min == pytest.approx(5.0, abs=0.1), "Delay should be updated to ~5 min"
