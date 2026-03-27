import re
import asyncio
import httpx
import pandas as pd
import math
import random
import logging

from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
import pytz

from config import API_KEY, BASE_URL, RESULTS_PER_STOP
from database import SessionLocal, engine
from exceptions import UpstreamUnavailableError
from metrics import poll_duration_seconds, upstream_errors_total, events_ingested_total, db_write_duration_seconds
from models import Departure

logger = logging.getLogger(__name__)

RAIL_PATTERN = re.compile(r'^[TLMS]\d$')

_http_client = httpx.AsyncClient(timeout=httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0))
_MAX_RETRIES = 3
_BASE_BACKOFF = 1.0  # seconds


async def _fetch_tfnsw(url: str, headers: dict, params: dict) -> httpx.Response:
    """Fetch from TfNSW API with timeout and jittered exponential backoff.

    Retries on network-level failures (timeout, connection error) only.
    Non-2xx responses are returned as-is — the caller decides what to do.
    """
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            return await _http_client.get(url, headers=headers, params=params)
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            if attempt == _MAX_RETRIES:
                raise UpstreamUnavailableError(
                    f"TfNSW unreachable after {_MAX_RETRIES} attempts: {e}"
                )
            delay = _BASE_BACKOFF * (2 ** (attempt - 1)) + random.uniform(0, 0.5)
            logger.warning(
                "TfNSW fetch attempt %d/%d failed (%s). Retrying in %.1fs",
                attempt, _MAX_RETRIES, e, delay,
            )
            await asyncio.sleep(delay)


async def get_departures(stop_id: str = "200060"):
    with poll_duration_seconds.labels(stop_id=stop_id).time():
        return await _get_departures_inner(stop_id)


def _rate_limit_context(response: httpx.Response) -> dict[str, str]:
    headers = getattr(response, "headers", {}) or {}
    return {
        "retry_after": headers.get("Retry-After", ""),
        "limit": headers.get("X-RateLimit-Limit", ""),
        "remaining": headers.get("X-RateLimit-Remaining", ""),
        "reset": headers.get("X-RateLimit-Reset", ""),
        "error_detail": headers.get("X-Error-Detail", ""),
    }


def _looks_rate_limited(response: httpx.Response) -> bool:
    if response.status_code == 429:
        return True
    if response.status_code != 403:
        return False
    headers = getattr(response, "headers", {}) or {}
    joined = " ".join(
        [
            headers.get("X-Error-Detail", ""),
            response.text[:300],
        ]
    ).lower()
    return any(token in joined for token in ("rate", "quota", "too many"))


async def _get_departures_inner(stop_id: str):
    headers = {
        "Authorization": f"apikey {API_KEY}"
    }

    sydney_tz = pytz.timezone("Australia/Sydney")
    now = datetime.now(sydney_tz)
    params = {
        "outputFormat": "rapidJSON",
        "coordOutputFormat": "EPSG:4326",
        "type_dm": "stop",
        "name_dm": stop_id,
        "departureMonitorMacro": "true",
        "TfNSWDM": "true",
        "version": "10.2.1.42",
        "itdDate": now.strftime("%Y%m%d"),
        "itdTime": now.strftime("%H%M"),
        "mode": "direct",
        "numberOfResultsDeparture": RESULTS_PER_STOP,
    }

    response = await _fetch_tfnsw(BASE_URL, headers=headers, params=params)
    if response.status_code != 200:
        ctx = _rate_limit_context(response)
        body_sample = (response.text or "")[:200].replace("\n", " ")
        logger.warning(
            "TfNSW non-200 stop_id=%s status=%s retry_after=%s remaining=%s limit=%s reset=%s detail=%s body=%s",
            stop_id,
            response.status_code,
            ctx["retry_after"] or "-",
            ctx["remaining"] or "-",
            ctx["limit"] or "-",
            ctx["reset"] or "-",
            ctx["error_detail"] or "-",
            body_sample,
        )
    if _looks_rate_limited(response):
        upstream_errors_total.labels(stop_id=stop_id).inc()
        raise UpstreamUnavailableError("RATE_LIMITED")
    if response.status_code != 200:
        upstream_errors_total.labels(stop_id=stop_id).inc()
        raise UpstreamUnavailableError(f"HTTP {response.status_code}: {response.text[:200]}")
    data = response.json()

    departures = []
    for event in data.get("stopEvents", []):
        try:
            transportation = event.get("transportation", {})
            destination = transportation.get("destination", {})
            location_props = event.get("location", {}).get("properties", {})
          
            departures.append({
                "line": transportation.get("disassembledName"),        # "L2"
                "lineName": transportation.get("number"),              # "L2 Randwick Line"
                "destination": destination.get("name"),                # "Randwick Light Rail, Randwick"
                "operator": transportation.get("operator", {}).get("name"),  # "Sydney Light Rail"
                "scheduled": event.get("departureTimePlanned"),
                "estimated": event.get("departureTimeEstimated"),
                "platform": location_props.get("platformName"),        # "Central Chalmers Street Light Rail"
                "realtime": event.get("isRealtimeControlled", False),
            })
        except Exception as e:
            logger.warning("Skipping event for stop %s: %s", stop_id, e)

    if not departures:
        logger.info("No departures found for stop %s", stop_id)
        return []

    df = pd.DataFrame(departures)

    if "scheduled" not in df.columns or "estimated" not in df.columns:
        logger.error("Missing expected columns for stop %s. Available: %s", stop_id, df.columns.tolist())
        return []
    
    df["scheduled_dt"] = pd.to_datetime(df["scheduled"], utc=True)
    df["estimated_dt"] = pd.to_datetime(df["estimated"], utc=True)
    df["delay_min"] = (df["estimated_dt"] - df["scheduled_dt"]).dt.total_seconds() / 60

    # save to DB
    db = SessionLocal()
    try:
        fetched_at = datetime.now(timezone.utc)

        rows = [
            {
                "line": row["line"],
                "line_name": row["lineName"],
                "destination": row["destination"],
                "operator": row["operator"],
                "platform": row["platform"],
                "scheduled": row["scheduled_dt"].to_pydatetime(),
                "estimated": row["estimated_dt"].to_pydatetime() if pd.notna(row["estimated_dt"]) else None,
                "delay_min": row["delay_min"] if pd.notna(row["delay_min"]) else None,
                "realtime": bool(row["realtime"]),
                "stop_id": stop_id,
                "fetched_at": fetched_at,
                "is_rail": bool(RAIL_PATTERN.match(row["line"] or "")),
            }
            for _, row in df.iterrows()
        ]

        insert_fn = pg_insert if engine.dialect.name == "postgresql" else sqlite_insert
        insert_stmt = insert_fn(Departure).values(rows)
        stmt = insert_stmt.on_conflict_do_update(
            index_elements=["line", "scheduled", "stop_id"],
            set_={
                "estimated": insert_stmt.excluded.estimated,
                "delay_min": insert_stmt.excluded.delay_min,
                "fetched_at": insert_stmt.excluded.fetched_at,
            }
        )
        with db_write_duration_seconds.labels(stop_id=stop_id).time():
            db.execute(stmt)
            db.commit()
        events_ingested_total.labels(stop_id=stop_id).inc(len(rows))
        logger.info("stop_id=%s fetched=%d upserted=%d", stop_id, len(rows), len(rows))
    except Exception as e:
        db.rollback()
        logger.error("DB error for stop %s: %s", stop_id, e)
    finally:
        db.close()
        
    result = df[["line", "lineName", "destination", "operator", "platform", "scheduled_dt", "estimated_dt", "delay_min", "realtime"]].copy()
    result = result.where(pd.notna(result), other=None)

    def clean(val):
        if isinstance(val, float) and math.isnan(val):
            return None
        return val

    return [
        {k: clean(v.isoformat() if hasattr(v, 'isoformat') else v) for k, v in row.items()}
        for row in result.to_dict(orient="records")
    ]
