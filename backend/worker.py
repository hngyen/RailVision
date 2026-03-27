"""
Standalone polling worker — runs as a separate process from the API.

Usage:
    python worker.py

Polls all tracked stations concurrently (bounded by SEMAPHORE_LIMIT) every
POLL_INTERVAL seconds and upserts departure data into the database.
"""

import asyncio
import logging
from services import get_departures

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

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


async def poll_all_stations() -> None:
    for name, stop_id in STATIONS.items():
        try:
            await get_departures(stop_id)
        except Exception as e:
            logger.error("Failed to poll %s (%s): %s", name, stop_id, e)
        await asyncio.sleep(INTER_REQUEST_DELAY)


async def _run() -> None:
    logger.info(
        "Worker started — polling %d stations every %ds (~%ds per cycle)",
        len(STATIONS), POLL_INTERVAL, len(STATIONS) * INTER_REQUEST_DELAY,
    )
    while True:
        await poll_all_stations()
        await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    asyncio.run(_run())
