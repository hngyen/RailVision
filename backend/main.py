from fastapi import FastAPI
from .services import get_departures
from .config import API_KEY, BASE_URL
app = FastAPI()

@app.get("/")
def root():
    return {"message": "NSW Trains API is running"}

@app.get("/departures/{stop_id}")
def departures(stop_id: str):
    return get_departures(stop_id)