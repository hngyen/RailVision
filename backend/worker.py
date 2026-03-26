"""
Standalone polling worker — runs as a separate process from the API.

Usage:
    python worker.py

This polls all tracked stations every 60 seconds and upserts departure
data into the database. Keeping this separate from the FastAPI process
means the API can scale independently (multiple uvicorn workers) without
spawning duplicate pollers.
"""

import time
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

POLL_INTERVAL = 60  # seconds


def poll_all_stations():
    for name, stop_id in STATIONS.items():
        try:
            get_departures(stop_id)
        except Exception as e:
            logger.error("Failed to poll %s (%s): %s", name, stop_id, e)


if __name__ == "__main__":
    logger.info("Worker started — polling %d stations every %ds", len(STATIONS), POLL_INTERVAL)
    while True:
        try:
            poll_all_stations()
        except Exception as e:
            logger.error("Poll cycle failed: %s", e)
        time.sleep(POLL_INTERVAL)
