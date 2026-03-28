# RailVision

**Real-time NSW train analytics platform with event-driven architecture, Redis-backed state management, and WebSocket push updates.**

[Live Demo](https://railvision-dash.vercel.app) | [API Docs](https://railvision-app-jpl5c.ondigitalocean.app/docs)

---

![RailVision Dashboard](./docs/screenshots/main_dashboard_rv.png)

---

## What it does

RailVision ingests live departure data from 31 Sydney train stations via the Transport for NSW API, processes it through a dedicated worker service, and serves real-time analytics through a FastAPI backend. The frontend receives instant updates via WebSocket — no polling required.

---

## Features

- **Real-time departure board** — live trains with platform, destination, and delay status, pushed via WebSocket
- **Interactive station map** — Leaflet map with 31 stations as primary navigation, markers sized by trip count and colored by delay severity
- **Line performance rankings** — T, L, M, and S lines ranked by average delay with on-time percentage
- **Delay heatmap** — day/hour grid showing peak disruption windows across the week
- **Hourly delay chart** — bar chart of average delays by hour (Sydney local time)
- **Per-station stats** — total trips, daily average, avg delay, worst line

---

## Screenshots

### Dashboard Overview
![Dashboard](./docs/screenshots/dashboard_rv.png)

### Interactive Station Map
![Map](./docs/screenshots/map_rv.png)

### Delay Heatmap
![Heatmap](./docs/screenshots/heatmap_rv.png)

### Live Departure Board
![Departures](./docs/screenshots/departures_rv.png)

---

## Architecture

```
                    ┌─────────────────┐
                    │   TfNSW API     │
                    └────────┬────────┘
                             │ polls every 15s
                    ┌────────▼────────┐
                    │     Worker      │  (standalone process)
                    │  - httpx async  │
                    │  - retry/backoff│
                    │  - rate limit   │
                    └───┬─────────┬───┘
                        │         │
              writes state    writes history
                        │         │
                  ┌─────▼──┐  ┌───▼──────────┐
                  │ Redis  │  │  PostgreSQL   │
                  │ (live) │  │  (analytics)  │
                  └─────┬──┘  └───┬──────────┘
            pub/sub │         │
                  ┌─────▼─────────▼──┐
                  │    API Server     │
                  │  GET /live   ← Redis (sub-5ms)
                  │  GET /analytics ← Postgres
                  │  WS  /ws     ← Redis Pub/Sub
                  └────────┬─────────┘
                           │
                  ┌────────▼────────┐
                  │    Frontend     │
                  │  React + Vite   │
                  │  WebSocket live │
                  └─────────────────┘
```

### Data flow

**Write path (Worker):** TfNSW API → parse & deduplicate → batch upsert to Postgres → write current state to Redis hashes → publish change events to Redis Pub/Sub

**Read path (API):** Live departures served from Redis (fast). Analytics queries served from Postgres (durable). WebSocket subscriptions receive push events from Redis Pub/Sub, filtered by station.

**Frontend:** Connects via WebSocket on station select. Receives instant updates when the worker detects a state change (new trip, delay update). Falls back to REST polling if WebSocket disconnects.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python, FastAPI, Uvicorn |
| Worker | Standalone async process, httpx with retry/backoff |
| Database | PostgreSQL (DigitalOcean) |
| Cache / State | Redis (DigitalOcean managed) |
| Real-time | WebSocket (FastAPI) + Redis Pub/Sub |
| ORM | SQLAlchemy 2.0, Alembic migrations |
| Data processing | Pandas |
| Observability | Prometheus metrics, structured logging |
| Frontend | React 19, Vite, Recharts, Leaflet |
| Deployment | DigitalOcean App Platform (API + Worker), Vercel (frontend) |
| Data source | Transport for NSW Open Data API |

---

## Key Engineering Decisions

**CQRS with Redis + Postgres** — live departure reads are served from Redis hashes (sub-5ms), while analytics queries hit Postgres for durable historical data. This separates the read and write paths so the API stays fast regardless of ingestion load.

**Event-driven WebSocket push** — the worker computes a fingerprint (MD5 of delay + estimated + platform) for each trip. Only when the fingerprint changes does it publish to Redis Pub/Sub. The API subscribes and fans out to WebSocket clients filtered by station. This eliminates unnecessary network traffic — the frontend only receives meaningful updates.

**Dedicated worker process** — ingestion runs as a separate DigitalOcean worker component with its own lifecycle. The API can restart, scale, or deploy independently without interrupting data collection. A Postgres advisory lock prevents duplicate polling if multiple worker instances start.

**Batch upsert with deduplication** — departures are uniquely identified by `(line, scheduled_time, stop_id)`. Before upserting, rows are deduplicated by conflict key with a quality scoring function (prefers rows with realtime data, estimated times, and platform info). This prevents Postgres cardinality violations and keeps the dataset clean.

**Resilient upstream integration** — TfNSW calls use httpx with explicit timeouts (5s connect, 10s read), jittered exponential backoff on failures, and rate limit detection (HTTP 429 + header inspection). On rate limit, the worker backs off exponentially up to 10 minutes.

**SQLite locally, PostgreSQL in production** — SQLAlchemy abstracts the DB layer so the same models work in both environments. Dialect-specific operations (upsert syntax, timezone functions) are handled with conditional branches.

**Proper timestamp handling** — all timestamps stored as `TIMESTAMPTZ` in Postgres. Analytics queries use `timezone('Australia/Sydney', ...)` for correct local time conversion, handling both AEDT and AEST automatically.

---

## Running Locally

### Prerequisites
- Python 3.12+
- Node.js 20+
- A [TfNSW Open Data](https://opendata.transport.nsw.gov.au/) API key
- Redis (optional — falls back to Postgres for live data)

### Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# create .env
echo "TFNSW_API_KEY=your_key_here" > .env
# optional: REDIS_URL=redis://localhost:6379 DATABASE_URL=postgresql://...

# run API server
uvicorn main:app --reload

# run worker (separate terminal)
python worker.py
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Update the `API` constant in `App.jsx` to point to your local backend if needed.

### Tests

```bash
cd backend
pytest tests/ -v
```

---

## Data source

Data is sourced from the [Transport for NSW Open Data API](https://opendata.transport.nsw.gov.au/) under the Transport for NSW open data licence.
