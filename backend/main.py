from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, Integer, text
import os
from database import engine, SessionLocal
from models import Departure
from exceptions import UpstreamUnavailableError
from schemas import DepartureOut
from services import get_departures
from config import API_KEY, BASE_URL
from typing import Optional
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://railvision-dash.vercel.app",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# background polling job
def poll_departures():
    for name, stop_id in STATIONS.items():
        get_departures(stop_id)

ENABLE_SCHEDULER = os.getenv("RAILVISION_ENABLE_SCHEDULER", "1").lower() in {"1", "true", "yes"}

if ENABLE_SCHEDULER:
    scheduler = BackgroundScheduler()
    scheduler.add_job(poll_departures, "interval", seconds=60)
    scheduler.start()

@app.api_route("/", methods=["GET", "HEAD"])
def root():
    return {"message": "RailVision API is running"}

@app.get("/departures/{stop_id}", response_model=list[DepartureOut])
def departures(stop_id: str):
    try:
        return get_departures(stop_id)
    except UpstreamUnavailableError as e:
        raise HTTPException(status_code=502, detail=e.message)

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
                Departure.scheduled + text("interval '11 hours'"), # real timestamp now
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

@app.get("/departures/live/{stop_id}", response_model=list[DepartureOut])
def live_departures(stop_id: str):
    try:
        deps = get_departures(stop_id)
    except UpstreamUnavailableError as e:
        raise HTTPException(status_code=502, detail=e.message)
    filtered = [d for d in deps if re.match(r'^[TLMS]\d$', str(d.get("line", "")))]
    return sorted(filtered, key=lambda x: x.get("scheduled_dt", ""))

@app.get("/analytics/delays/by-day-hour")
def delays_by_day_hour(stop_id: Optional[str] = None):
    db = SessionLocal()
    try:
        is_postgres = "postgresql" in str(engine.url)

        if is_postgres:
            hour_expr = func.to_char(
                Departure.scheduled + text("interval '11 hours'"),
                'HH24'
            )
            day_expr = func.to_char(
                Departure.scheduled + text("interval '11 hours'"),
                'D'
            )
        else:
            hour_expr = func.strftime('%H', Departure.scheduled, '+11 hours')
            day_expr = func.strftime('%w', Departure.scheduled, '+11 hours')

        query = (
            db.query(
                day_expr.label("day"),
                hour_expr.label("hour"),
                func.avg(Departure.delay_min).label("avg_delay"),
                func.count(Departure.id).label("total_trips"),
            )
            .filter(Departure.line.op('~')('^[TLMS][0-9]$'))
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
            .filter(Departure.line.op('~')('^[TLMS][0-9]$'))
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
            .filter(Departure.line.op('~')('^[TLMS][0-9]$'))
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
