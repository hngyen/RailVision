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




models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["railvision-frontend.vercel.app"],
    allow_methods=["*"],
    allow_headers=["*"],
)
# background polling job
def poll_departures():
    print("Polling departures...")
    get_departures("200060")  # Central, add more stops later

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
def delay_by_lines():
    db = SessionLocal()
    try:
        results = (
            db.query(
                Departure.line,
                func.avg(Departure.delay_min).label("avg_delay"),
                func.count(Departure.id).label("total_trips"),
                func.sum((Departure.delay_min > 1).cast(Integer)).label("delayed_trips"),
            )
            .group_by(Departure.line)
            .filter(or_(
                Departure.line.like("T%"),
                Departure.line.like("L%"),
                Departure.line.like("M%"),
                Departure.line.like("S%"),
            ))
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
def worst_lines():
    db = SessionLocal()
    try:
        results = (
            db.query(
                Departure.line,
                Departure.line_name,
                func.avg(Departure.delay_min).label("avg_delay"),
                func.count(Departure.id).label("total_trips"),
                func.sum((Departure.delay_min > 1).cast(Integer)).label("delayed_trips"),
            )
            .group_by(Departure.line, Departure.line_name)
            .filter(or_(
                Departure.line.like("T%"),
                Departure.line.like("L%"),
                Departure.line.like("M%"),
                Departure.line.like("S%"),
            ))
            .having(func.count(Departure.id) >= 1)  # ignore lines with tiny sample size
            .order_by(func.avg(Departure.delay_min).desc().nullslast())
            .all()
        )
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
def delays_by_hour():
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
        
        results = (
            db.query(
                hour_expr.label("hour"),
                func.avg(Departure.delay_min).label("avg_delay"),
                func.count(Departure.id).label("total_trips"),
            )
            .filter(or_(
                Departure.line.like("T%"),
                Departure.line.like("L%"),
                Departure.line.like("M%"),
                Departure.line.like("S%"),
            ))
            .group_by(hour_expr)
            .order_by(hour_expr)
            .all()
        )
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
    filtered = [d for d in deps if str(d.get("line", "")).startswith(("T", "L", "M", "S"))]
    return sorted(filtered, key=lambda x: x.get("scheduled_dt", ""))