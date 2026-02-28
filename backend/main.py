from fastapi import FastAPI
from .database import engine
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import func, Integer
from .database import SessionLocal

from .services import get_departures
from .config import API_KEY, BASE_URL
from .models import Departure
from . import models


models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# background polling job
def poll_departures():
    print("Polling departures...")
    get_departures("200060")  # Central, add more stops later

scheduler = BackgroundScheduler()
scheduler.add_job(poll_departures, "interval", seconds=60)
scheduler.start()

@app.get("/")
def root():
    return {"message": "RailVision API is running"}

@app.get("/departures/{stop_id}")
def departures(stop_id: str):
    return get_departures(stop_id)

@app.get("/analytics/delays")
def delay_stats():
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
            .order_by(func.avg(Departure.delay_min).desc())
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