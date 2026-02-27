import requests
from .config import API_KEY, BASE_URL
from datetime import datetime

def get_departures(stop_id: str = "10111010"):
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
        "numberOfResultsDeparture": "40"
    }
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

    return departures