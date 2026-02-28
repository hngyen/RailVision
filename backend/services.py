import requests
import pandas as pd
import math

from datetime import datetime, timezone

from config import API_KEY, BASE_URL
from database import SessionLocal
from models import Departure

def get_departures(stop_id: str = "200060"):
    headers = {
        "Authorization": f"apikey {API_KEY}"
    }
    now = datetime.now()
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
        "numberOfResultsDeparture": "40",
    }

    # if unsuccessful response
    response = requests.get(BASE_URL, headers=headers, params=params)
    if response.status_code != 200:
        return {"error": response.text}
    data = response.json()

    departures = []
    for event in data.get("stopEvents", []):
        try:
            transportation = event.get("transportation", {})
            destination = transportation.get("destination", {})
            location_props = event.get("location", {}).get("properties", {})
          
            departures.append({
                "line": transportation.get("disassembledName"),        # e.g. "L2"
                "lineName": transportation.get("number"),              # e.g. "L2 Randwick Line"
                "destination": destination.get("name"),                # e.g. "Randwick Light Rail, Randwick"
                "operator": transportation.get("operator", {}).get("name"),  # e.g. "Sydney Light Rail"
                "scheduled": event.get("departureTimePlanned"),
                "estimated": event.get("departureTimeEstimated"),
                "platform": location_props.get("platformName"),        # e.g. "Central Chalmers Street Light Rail"
                "realtime": event.get("isRealtimeControlled", False),
            })
        except Exception as e:
            print(f"Skipping event: {e}")
    
    # pandas for delay calculation
    df = pd.DataFrame(departures)
    df["scheduled_dt"] = pd.to_datetime(df["scheduled"], utc=True)
    df["estimated_dt"] = pd.to_datetime(df["estimated"], utc=True)
    df["delay_min"] = (df["estimated_dt"] - df["scheduled_dt"]).dt.total_seconds() / 60

    # save to DB
    db = SessionLocal()
    try:
        fetched_at = datetime.now(timezone.utc).isoformat()
        for _, row in df.iterrows():
            record = Departure(
                line=row["line"],
                line_name=row["lineName"],
                destination=row["destination"],
                operator=row["operator"],
                platform=row["platform"],
                scheduled=row["scheduled_dt"].isoformat(),
                estimated=row["estimated_dt"].isoformat() if pd.notna(row["estimated_dt"]) else None,
                delay_min=row["delay_min"] if pd.notna(row["delay_min"]) else None,
                realtime=row["realtime"],
                stop_id=stop_id,
                fetched_at=fetched_at,
            )
            db.add(record)
        db.commit()
        print(f"Saved {len(df)} departures to DB")
    except Exception as e:
        db.rollback()
        print(f"DB save error: {e}")
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