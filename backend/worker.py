"""
Standalone polling worker — runs as a separate process from the API.

Usage:
    python worker.py

Polls all tracked stations every POLL_INTERVAL seconds and upserts departure
data into the database.
"""

import asyncio
import logging
import os
from sqlalchemy import text
from services import get_departures
from database import engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}

STATIONS = {
    "Cabramatta": "216620",
    "Liverpool": "217010",
    "Central": "200060",
    "Town Hall": "200070",
    "Redfern": "201510",
    "Parramatta": "215020",
    "Wynyard": "200080",
    "Strathfield": "213510",
    "Martin Place": "200090",
    "Chatswood": "206710",
    "Circular Quay": "200010",
    "Bondi Junction": "202220",
    "Burwood": "213410",
    "Gadigal": "2000434",
    "North Sydney": "206010",
    "Hurstville": "222010",
    "Wolli Creek": "220510",
    "Blacktown": "214810",
    "Epping": "212110",
    "Mascot": "202010",
    "Green Square": "201710",
    "Victoria Cross": "2060444",
    "Ashfield": "213110",
    "Seven Hills": "214710",
    "Sydenham": "204410",
    "Lidcombe": "214110",
    "Museum": "200040",
    "St James": "200050",
    "Kings Cross": "201110",
    "Hornsby": "207710",
    "Rhodes": "213810",
    "Auburn": "214410",
}

POLL_INTERVAL = 60   # seconds between full poll cycles
INTER_REQUEST_DELAY = 1.0  # seconds between each station request
_rate_limit_backoff = 60  # grows on consecutive rate limits
_POLL_LOCK_ID = 220032022  # shared lock id for all poller instances


def _acquire_poll_lock():
    if engine.dialect.name != "postgresql":
        return None

    conn = engine.connect()
    locked = bool(
        conn.execute(
            text("SELECT pg_try_advisory_lock(:lock_id)"),
            {"lock_id": _POLL_LOCK_ID},
        ).scalar()
    )
    if not locked:
        conn.close()
        return False
    return conn


def _release_poll_lock(conn) -> None:
    if not conn:
        return
    try:
        conn.execute(
            text("SELECT pg_advisory_unlock(:lock_id)"),
            {"lock_id": _POLL_LOCK_ID},
        )
    finally:
        conn.close()


async def poll_all_stations() -> None:
    global _rate_limit_backoff
    lock_conn = _acquire_poll_lock()
    if lock_conn is False:
        logger.info("Skipping poll cycle (another instance holds the poll lock)")
        return

    try:
        for name, stop_id in STATIONS.items():
            try:
                await get_departures(stop_id)
                _rate_limit_backoff = 60  # reset on success
            except Exception as e:
                msg = str(e)
                if "RATE_LIMITED" in msg:
                    logger.warning(
                        "Rate limited by TfNSW — backing off %ds", _rate_limit_backoff
                    )
                    await asyncio.sleep(_rate_limit_backoff)
                    _rate_limit_backoff = min(_rate_limit_backoff * 2, 600)  # cap at 10min
                    return
                logger.error("Failed to poll %s (%s): %s", name, stop_id, e)
            await asyncio.sleep(INTER_REQUEST_DELAY)
    finally:
        _release_poll_lock(lock_conn)


async def _run() -> None:
    if not _env_bool("RUN_POLLER", True):
        logger.info("RUN_POLLER=false; worker polling disabled")
        while True:
            await asyncio.sleep(3600)

    logger.info(
        "Worker started — polling %d stations every %ds (~%ds per cycle)",
        len(STATIONS), POLL_INTERVAL, len(STATIONS) * INTER_REQUEST_DELAY,
    )
    while True:
        await poll_all_stations()
        await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    asyncio.run(_run())
