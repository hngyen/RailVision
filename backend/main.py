from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, Integer
from database import engine, SessionLocal
from models import Departure
from schemas import DepartureOut
from typing import Optional
from datetime import datetime, timezone, timedelta
import asyncio


async def _poll_loop():
    """Run the worker polling loop as a background asyncio task."""
    from worker import poll_all_stations, POLL_INTERVAL
    while True:
        poll_all_stations()
        await asyncio.sleep(POLL_INTERVAL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_poll_loop())
    yield
    task.cancel()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://railvision-dash.vercel.app",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.api_route("/", methods=["GET", "HEAD"])
def root():
    return {"message": "RailVision API is running"}

def _query_departures(stop_id: str, rail_only: bool = False) -> list[dict]:
    """Read upcoming departures for a stop from the database."""
    db = SessionLocal()
    try:
        window_start = datetime.now(timezone.utc) - timedelta(minutes=5)
        query = (
            db.query(Departure)
            .filter(Departure.stop_id == stop_id)
            .filter(Departure.scheduled >= window_start)
        )
        if rail_only:
            query = query.filter(Departure.is_rail.is_(True))
        rows = query.order_by(Departure.scheduled).all()
        return [
            {
                "line": r.line,
                "lineName": r.line_name,
                "destination": r.destination,
                "operator": r.operator,
                "platform": r.platform,
                "scheduled_dt": r.scheduled.isoformat() if r.scheduled else None,
                "estimated_dt": r.estimated.isoformat() if r.estimated else None,
                "delay_min": r.delay_min,
                "realtime": r.realtime,
            }
            for r in rows
        ]
    finally:
        db.close()


@app.get("/departures/{stop_id}", response_model=list[DepartureOut])
def departures(stop_id: str):
    return _query_departures(stop_id)

@app.get("/analytics/delays/by-line")
def delay_by_lines(stop_id: Optional[str] = None):
    db = SessionLocal()
    try:
        query = db.query(
            Departure.line,
            func.avg(Departure.delay_min).label("avg_delay"),
            func.count(Departure.id).label("total_trips"),
            func.sum((Departure.delay_min > 1).cast(Integer)).label("delayed_trips"),
        ).filter(Departure.is_rail.is_(True))

        if stop_id:
            query = query.filter(Departure.stop_id == stop_id)

        results = (
            query.group_by(Departure.line)
            .order_by(func.avg(Departure.delay_min).desc().nullslast())
            .all()
        )

        return [
            {
                "line": r.line,
                "avg_delay_min": round(r.avg_delay, 2) if r.avg_delay else 0,
                "total_trips": r.total_trips,
                "delayed_trips": r.delayed_trips or 0,
            }
            for r in results
        ]
    finally:
        db.close()

@app.get("/analytics/worst-lines")
def worst_lines(stop_id: Optional[str] = None):
    db = SessionLocal()
    try:
        query = (
            db.query(
                Departure.line,
                Departure.line_name,
                func.avg(Departure.delay_min).label("avg_delay"),
                func.count(Departure.id).label("total_trips"),
                func.sum((Departure.delay_min > 1).cast(Integer)).label("delayed_trips"),
            )
            .group_by(Departure.line, Departure.line_name)
            .filter(Departure.is_rail.is_(True))
        )
        if stop_id:
            query = query.filter(Departure.stop_id == stop_id)
        
        results = query.having(func.count(Departure.id) >= 1).order_by(func.avg(Departure.delay_min).desc().nullslast()).all()
        return [
            {
                "line": r.line,
                "lineName": r.line_name,
                "avg_delay_min": round(r.avg_delay, 2) if r.avg_delay else 0,
                "total_trips": r.total_trips,
                "delayed_trips": r.delayed_trips or 0,
                "on_time_pct": round((1 - (r.delayed_trips or 0) / r.total_trips) * 100, 1),
            }
            for r in results
        ]
    finally:
        db.close()

@app.get("/analytics/delays/by-hour")
def delays_by_hour(stop_id: Optional[str] = None):
    db = SessionLocal()
    try:
        is_postgres = "postgresql" in str(engine.url)
        if is_postgres:
            hour_expr = func.to_char(
                func.timezone('Australia/Sydney', Departure.scheduled),
                'HH24'
            )
        else:
            hour_expr = func.strftime('%H', Departure.scheduled, 'localtime')

        query = (
            db.query(
                hour_expr.label("hour"),
                func.avg(Departure.delay_min).label("avg_delay"),
                func.count(Departure.id).label("total_trips"),
            ).filter(Departure.is_rail.is_(True))
        )

        if stop_id:
            query = query.filter(Departure.stop_id == stop_id)

        results = query.group_by(hour_expr).order_by(hour_expr).all()
        return [
            {
                "hour": int(r.hour),
                "avg_delay_min": round(r.avg_delay, 2) if r.avg_delay else 0,
                "total_trips": r.total_trips,
            }
            for r in results
        ]
    finally:
        db.close()

@app.get("/departures/live/{stop_id}", response_model=list[DepartureOut])
def live_departures(stop_id: str):
    return _query_departures(stop_id, rail_only=True)

@app.get("/analytics/delays/by-day-hour")
def delays_by_day_hour(stop_id: Optional[str] = None):
    db = SessionLocal()
    try:
        is_postgres = "postgresql" in str(engine.url)

        if is_postgres:
            hour_expr = func.to_char(
                func.timezone('Australia/Sydney', Departure.scheduled),
                'HH24'
            )
            day_expr = func.to_char(
                func.timezone('Australia/Sydney', Departure.scheduled),
                'D'
            )
        else:
            hour_expr = func.strftime('%H', Departure.scheduled, 'localtime')
            day_expr = func.strftime('%w', Departure.scheduled, 'localtime')

        query = (
            db.query(
                day_expr.label("day"),
                hour_expr.label("hour"),
                func.avg(Departure.delay_min).label("avg_delay"),
                func.count(Departure.id).label("total_trips"),
            )
            .filter(Departure.is_rail.is_(True))
        )
        if stop_id:
            query = query.filter(Departure.stop_id == stop_id)

        results = query.group_by(day_expr, hour_expr).order_by(day_expr, hour_expr).all()
        return [
            {
                "day": int(r.day),
                "hour": int(r.hour),
                "avg_delay_min": round(r.avg_delay, 2) if r.avg_delay else 0,
                "total_trips": r.total_trips,
            }
            for r in results
        ]
    finally:
        db.close()

@app.get("/analytics/stations/summary")
def stations_summary():
    db = SessionLocal()
    try:
        results = (
            db.query(
                Departure.stop_id,
                func.avg(Departure.delay_min).label("avg_delay"),
                func.count(Departure.id).label("total_trips"),
            )
            .filter(Departure.is_rail.is_(True))
            .group_by(Departure.stop_id)
            .all()
        )

        # worst line per station
        worst = (
            db.query(
                Departure.stop_id,
                Departure.line,
                func.avg(Departure.delay_min).label("avg_delay"),
            )
            .filter(Departure.is_rail.is_(True))
            .group_by(Departure.stop_id, Departure.line)
            .order_by(Departure.stop_id, func.avg(Departure.delay_min).desc())
            .all()
        )

        worst_by_station = {}
        for r in worst:
            if r.stop_id not in worst_by_station:
                worst_by_station[r.stop_id] = r.line

        return {
            r.stop_id: {
                "avg_delay": round(r.avg_delay, 2) if r.avg_delay else 0,
                "total_trips": r.total_trips,
                "worst_line": worst_by_station.get(r.stop_id)
            }
            for r in results
        }
    finally:
        db.close()
