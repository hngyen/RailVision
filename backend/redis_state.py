"""
Redis state layer for RailVision.

Responsibilities:
  - Store current trip state as Redis hashes (fast read path for live endpoints)
  - Detect meaningful state changes (diff) between poll cycles
  - Publish change events to a Pub/Sub channel for WebSocket fan-out

Key schema:
  rv:trip:{stop_id}:{line}:{scheduled_ts}  → Hash of current trip state
  rv:stop:{stop_id}                        → Set of trip keys for that stop
  rv:changes                               → Pub/Sub channel for state-change events
"""

import hashlib
import json
import logging
from datetime import datetime, timezone

import redis.asyncio as redis

from config import REDIS_URL

logger = logging.getLogger(__name__)

TRIP_TTL = 7200  # 2 hours — stale trips auto-expire
CHANNEL = "rv:changes"

_pool: redis.Redis | None = None


async def get_redis() -> redis.Redis | None:
    """Lazy-init a shared async Redis connection pool."""
    global _pool
    if _pool is not None:
        return _pool
    if not REDIS_URL:
        logger.warning("REDIS_URL not set — Redis state layer disabled")
        return None
    _pool = redis.from_url(REDIS_URL, decode_responses=True)
    # Verify connectivity
    await _pool.ping()
    logger.info("Redis connected")
    return _pool


def _trip_key(stop_id: str, line: str, scheduled_iso: str) -> str:
    """Deterministic key for a single trip."""
    return f"rv:trip:{stop_id}:{line}:{scheduled_iso}"


def _stop_key(stop_id: str) -> str:
    """Key for the set of all trip keys at a stop."""
    return f"rv:stop:{stop_id}"


def _fingerprint(trip: dict) -> str:
    """Hash the fields that matter for change detection."""
    sig = f"{trip.get('estimated')}|{trip.get('delay_min')}|{trip.get('platform')}"
    return hashlib.md5(sig.encode()).hexdigest()


async def update_trips(stop_id: str, departures: list[dict]) -> list[dict]:
    """Write trip state to Redis; return list of change events.

    Each departure dict should have: line, destination, platform,
    scheduled_dt, estimated_dt, delay_min, realtime, lineName.

    Returns a list of change event dicts (only for trips whose state
    actually changed since the last poll).
    """
    r = await get_redis()
    if r is None:
        return []

    stop_set_key = _stop_key(stop_id)
    changes = []
    current_keys = set()
    pipe = r.pipeline()

    for dep in departures:
        scheduled_iso = dep.get("scheduled_dt") or ""
        line = dep.get("line") or ""
        key = _trip_key(stop_id, line, scheduled_iso)
        current_keys.add(key)

        new_fp = _fingerprint(dep)

        # Check if this trip already exists with the same fingerprint
        old_fp = await r.hget(key, "_fp")

        trip_data = {
            "line": line,
            "lineName": dep.get("lineName") or "",
            "destination": dep.get("destination") or "",
            "platform": dep.get("platform") or "",
            "scheduled_dt": scheduled_iso,
            "estimated_dt": dep.get("estimated_dt") or "",
            "delay_min": str(dep.get("delay_min") or 0),
            "realtime": str(dep.get("realtime", False)),
            "stop_id": stop_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "_fp": new_fp,
        }

        pipe.hset(key, mapping=trip_data)
        pipe.expire(key, TRIP_TTL)
        pipe.sadd(stop_set_key, key)

        if old_fp is None:
            changes.append({
                "stop_id": stop_id,
                "line": line,
                "event_type": "new_trip",
                "delay_min": dep.get("delay_min"),
                "scheduled_dt": scheduled_iso,
            })
        elif old_fp != new_fp:
            changes.append({
                "stop_id": stop_id,
                "line": line,
                "event_type": "update",
                "delay_min": dep.get("delay_min"),
                "scheduled_dt": scheduled_iso,
            })

    pipe.expire(stop_set_key, TRIP_TTL)
    await pipe.execute()

    # Publish changes
    if changes:
        for event in changes:
            await r.publish(CHANNEL, json.dumps(event))
        logger.info(
            "stop_id=%s redis_writes=%d changes_published=%d",
            stop_id, len(departures), len(changes),
        )

    return changes


async def get_live_departures(stop_id: str) -> list[dict]:
    """Read all current trips for a stop from Redis.

    Returns a list of departure dicts, sorted by scheduled time.
    Falls back to empty list if Redis is unavailable.
    """
    r = await get_redis()
    if r is None:
        return []

    stop_set_key = _stop_key(stop_id)
    trip_keys = await r.smembers(stop_set_key)

    if not trip_keys:
        return []

    pipe = r.pipeline()
    for key in trip_keys:
        pipe.hgetall(key)
    results = await pipe.execute()

    departures = []
    for data in results:
        if not data or not data.get("line"):
            continue
        departures.append({
            "line": data["line"],
            "lineName": data.get("lineName"),
            "destination": data.get("destination"),
            "platform": data.get("platform"),
            "scheduled_dt": data.get("scheduled_dt"),
            "estimated_dt": data.get("estimated_dt"),
            "delay_min": float(data["delay_min"]) if data.get("delay_min") else None,
            "realtime": data.get("realtime") == "True",
        })

    departures.sort(key=lambda d: d.get("scheduled_dt") or "")
    return departures


async def close():
    """Shut down the Redis connection pool."""
    global _pool
    if _pool:
        await _pool.aclose()
        _pool = None
