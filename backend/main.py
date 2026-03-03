from fastapi import FastAPI
from fastapi.responses import Response
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, Integer, or_, cast, text
from sqlalchemy.types import String
from sqlalchemy.types import TIMESTAMP
import models
from database import engine, SessionLocal
from models import Departure
from services import get_departures
from config import API_KEY, BASE_URL
from typing import Optional
import re

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIONS = {
    "Central": "200060",
    "Town Hall": "200070",
    "Parramatta": "215020",
    "Strathfield": "213510",
    "Redfern": "201510",
    "Cabramatta": "216620"
}

# background polling job
def poll_departures():
    for name, stop_id in STATIONS.items():
        get_departures(stop_id)

scheduler = BackgroundScheduler()
scheduler.add_job(poll_departures, "interval", seconds=60)
scheduler.start()

@app.api_route("/", methods=["GET", "HEAD"])
def root():
    return {"message": "RailVision API is running"}

@app.get("/departures/{stop_id}")
def departures(stop_id: str):
    return get_departures(stop_id)

@app.get("/analytics/delays/by-line")
def delay_by_lines(stop_id: Optional[str] = None):
    db = SessionLocal()
    try:
        query = db.query(
            Departure.line,
            func.avg(Departure.delay_min).label("avg_delay"),
            func.count(Departure.id).label("total_trips"),
            func.sum((Departure.delay_min > 1).cast(Integer)).label("delayed_trips"),
        ).filter(Departure.line.op('~')('^[TLMS][0-9]$'))

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
            .filter(Departure.line.op('~')('^[TLMS][0-9]$'))
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
                cast(Departure.scheduled, TIMESTAMP) + text("interval '11 hours'"),
                'HH24'
            )
        else:
            hour_expr = func.strftime('%H', Departure.scheduled, '+11 hours')

        query = (
            db.query(
                hour_expr.label("hour"),
                func.avg(Departure.delay_min).label("avg_delay"),
                func.count(Departure.id).label("total_trips"),
            ).filter(Departure.line.op('~')('^[TLMS][0-9]$'))
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

@app.get("/departures/live/{stop_id}")
def live_departures(stop_id: str):
    deps = get_departures(stop_id)
    filtered = [d for d in deps if re.match(r'^[TLMS]\d$', str(d.get("line", "")))]
    return sorted(filtered, key=lambda x: x.get("scheduled_dt", ""))