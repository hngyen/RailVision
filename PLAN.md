# RailVision V2 — Comprehensive Improvement Plan

---

## Table of Contents

1. [KPIs & Baseline Metrics](#1-kpis--baseline-metrics)
2. [Bug Fixes & Issues (Prioritised)](#2-bug-fixes--issues-prioritised)
3. [Architecture Upgrade Roadmap](#3-architecture-upgrade-roadmap)
4. [V2 Component Spec](#4-v2-component-spec)
5. [Implementation Checklist](#5-implementation-checklist)

---

## 1. KPIs & Baseline Metrics

Measure these **before touching any code**. Rerun after each major fix and tag results by version (`baseline_v1`, `v1_ingestion_fix`, `v2_worker_split`, `v3_redis_ws`). Save in `docs/metrics/` as CSV + one chart per KPI.

| KPI | Definition |
|-----|-----------|
| `ingestion_completeness` | `persisted_rows / fetched_rows` per poll cycle |
| `duplicate_rate` | `duplicate_keys / total_rows` for `(line, scheduled, stop_id)` |
| `API reliability` | 5xx rate on public endpoints |
| `API latency` | p50/p95 for `/departures/live`, `/analytics/worst-lines`, `/analytics/delays/by-hour` |
| `freshness_lag_seconds` | `now - latest_fetched_at` |
| `upstream_load` | TfNSW requests/min as user count grows |

---

## 2. Bug Fixes & Issues (Prioritised)

Issues are ordered by impact — correctness first, then stability, then polish.

---

### Issue 1 — Set Up Smoke Tests (Safety Net)

**Files:** `backend/tests/test_api_smoke.py`, `backend/tests/test_services_contract.py`  
**Problem:** No tests or CI means every refactor is a blind guess.  
**Impact:** You can "fix" things and accidentally break other flows with no warning.

**Fix:**
- Create `tests/test_api_smoke.py` — test root + one analytics endpoint.
- Create `tests/test_services_contract.py` — test `get_departures()` return contract.
- Run tests before and after each subsequent step; keep failure screenshots/notes.

---

### Issue 2 — Batch Upsert Bug (Single-Row Data Loss)

**Files:** `backend/services.py:82`, `backend/services.py:97`, `backend/services.py:115`  
**Problem:** The ingestion loop only persists **one row per poll cycle** — the last one. All other departures are silently discarded.  
**Impact:** Data loss, inaccurate analytics, misleading dashboards.

**Fix:**
```python
# Build full list from dataframe
rows = [...]  # all parsed departures

# One batch upsert
insert(...).values(rows).on_conflict_do_update(...)

# Remove unused `record` variable
# Add structured log per stop:
{"stop_id": ..., "fetched": ..., "upserted": ...}
```
**Verify:** Compare `fetched_count` vs `upserted_count` for one stop over multiple runs.

---

### Issue 3 — Inconsistent Return Types in `get_departures()`

**Files:** `backend/services.py:38`, `backend/services.py:65`, `backend/main.py:187`  
**Problem:** Function returns `list`, `dict`, or `None` depending on the code path.  
**Impact:** Runtime crashes in `/departures/live/{stop_id}` and unpredictable API behaviour.

**Fix:**
- Add `backend/schemas.py` with `DepartureOut` and `ErrorOut` Pydantic models.
- Add `backend/exceptions.py` with `UpstreamUnavailableError`.
- Service always returns `list[DepartureDTO]`; raises `UpstreamUnavailableError` on failure.
- Route maps exception → `HTTPException(status_code=502)`.

**Verify:** Force an upstream failure; confirm the response is still valid JSON with a consistent error shape.

---

### Issue 4 — Introduce Alembic Before Schema Work

**Files:** `backend/main.py:16`, `backend/models.py:21`  
**Problem:** Runtime `create_all` causes schema drift between local and prod. Constraints and indexes in models are not guaranteed to exist.  
**Impact:** Local/prod divergence; hard-to-trust data model.

**Fix:**
```bash
alembic init backend/alembic/
# Create baseline revision
# Remove create_all() from app startup
```
**Verify:** Fresh DB + `alembic upgrade head` builds the correct schema end-to-end.

---

### Issue 5 — Timestamps Stored as Strings

**Files:** `backend/models.py:14`, `backend/models.py:15`, `backend/models.py:19`  
**Problem:** `scheduled`, `estimated`, and `fetched_at` are stored as plain strings.  
**Impact:** Expensive casts on every query, fragile ordering, no index support, dirty analytics.

**Migration SQL:**
```sql
ALTER TABLE departures ADD COLUMN scheduled_ts  TIMESTAMPTZ;
ALTER TABLE departures ADD COLUMN estimated_ts  TIMESTAMPTZ;
ALTER TABLE departures ADD COLUMN fetched_at_ts TIMESTAMPTZ;

UPDATE departures
SET scheduled_ts  = scheduled::timestamptz,
    estimated_ts  = NULLIF(estimated, '')::timestamptz,
    fetched_at_ts = fetched_at::timestamptz;

-- Deduplicate: keep latest fetched_at_ts per logical trip
CREATE UNIQUE INDEX uq_departure_trip      ON departures(line, scheduled_ts, stop_id);
CREATE INDEX        idx_departures_stop_ts ON departures(stop_id, scheduled_ts DESC);
```
Update `backend/models.py` to use `DateTime(timezone=True)` and update all reads/writes accordingly. Drop legacy string columns once backfill is confirmed.

**Verify:** Uniqueness violation occurs on a duplicate insert attempt.

---

### Issue 6 — PostgreSQL Regex Operator Breaks SQLite

**Files:** `backend/main.py:93`, `backend/main.py:129`, `backend/main.py:167`, `backend/main.py:217`  
**Problem:** `~` operator is Postgres-only; all local analytics queries fail.  
**Impact:** "Works in prod only" development experience.

**Fix:**
- Add `is_rail BOOLEAN NOT NULL DEFAULT FALSE` via migration.
- Set `is_rail` in `backend/services.py` during ingestion parsing using an allowlist.
- Replace all regex filters with `Departure.is_rail.is_(True)`.

**Verify:** Same analytics endpoints work on both SQLite (local) and Postgres (prod).

---

### Issue 7 — Hardcoded +11h Timezone Offset

**Files:** `backend/main.py:156`, `backend/main.py:199`  
**Problem:** Offset is hardcoded as +11, which is only valid during AEDT (DST). AEST is +10.  
**Impact:** Aggregations are wrong for 5 months of the year.

**Fix:**
```sql
-- Postgres: use named timezone, not a manual offset
timezone('Australia/Sydney', scheduled_ts)
-- Then extract day/hour from the result
```
Remove all manual `+ timedelta(hours=11)` style offsets from the codebase.

**Verify:** Test known timestamps in both DST (Oct–Apr) and non-DST (Apr–Oct) months.

---

### Issue 8 — Scheduler Starts on Import (Multi-Worker Race)

**Files:** `backend/main.py:72`  
**Problem:** Scheduler initialises at import time — unsafe with Uvicorn `--reload` or multi-worker deployments.  
**Impact:** Duplicate pollers, racey writes, inflated TfNSW API usage.

**Fix:**
- Create `backend/worker.py` as a dedicated entrypoint for the polling loop.
- Remove all scheduler setup from `backend/main.py`.
- Update `Procfile` / `railway.json` to run `worker.py` as a separate service.

**Verify:** API process can restart without disrupting ingestion continuity.

---

### Issue 9 — Read Endpoint Has Write Side Effects

**Files:** `backend/main.py:185`, `backend/main.py:80`  
**Problem:** `/departures/live/{stop_id}` triggers a live TfNSW fetch + DB write on every user request.  
**Impact:** User traffic amplifies upstream API load; possible rate-limiting; tightly coupled read/write paths.

**Fix:**
- Keep all ingestion exclusively in the worker process.
- `/departures/live/{stop_id}` reads from Redis current state or DB snapshot only — never calls TfNSW directly.

---

### Issue 10 — No Timeout/Retry on Upstream Calls

**Files:** `backend/services.py:37`  
**Problem:** HTTP calls to TfNSW have no timeout, retry, or backoff logic.  
**Impact:** A slow or dropped response hangs the entire ingestion loop indefinitely.

**Fix:**
```python
# Use httpx with explicit timeout and retry wrapper
client = httpx.AsyncClient(timeout=httpx.Timeout(connect=3.0, read=10.0))
# Add retry wrapper with jittered exponential backoff
# Log attempt count and latency per call
```

---

### Issue 11 — Sequential Polling Contradicts README Concurrency Claim

**Files:** `backend/main.py:68`, `README.md:68`  
**Problem:** Stops are polled sequentially, not concurrently, despite the README claiming otherwise.  
**Impact:** Slower full-cycle time; stations polled last are more stale.

**Fix:**
```python
# Async worker with bounded concurrency
semaphore = asyncio.Semaphore(6)  # 5–8 concurrent stops
async with semaphore:
    await poll_stop(stop_id)
# Track per-stop success/failure metrics
```

---

### Issue 12 — No Observability

**Files:** Cross-cutting across all backend files  
**Problem:** No structured logs, no metrics endpoint, no correlation IDs.  
**Impact:** Incidents are hard to diagnose; architecture maturity is invisible to reviewers.

**Fix — Metrics to expose at `/metrics`:**
- `poll_duration_seconds` (histogram)
- `upstream_error_rate` (counter)
- `events_emitted_total` (counter)
- `websocket_clients_active` (gauge)
- `db_write_latency_seconds` (histogram)

**Fix — Logging:**
- Emit structured JSON logs with `correlation_id`, `stop_id`, `level`, `timestamp`.

---

### Issue 13 — Brittle Frontend Data Handling

**Files:** `frontend/src/App.jsx:177`, `frontend/src/StationMap.jsx:83`  
**Problem:** Missing error handling on fetches; stale map markers not cleared on update.  
**Impact:** Silently broken UI; hangs on loading; outdated visuals persist after data refresh.

**Fix:**
```js
// Wrap all fetches in try/catch/finally
// Separate marker initialisation effect from marker update effect
// Maintain marker refs; update styles and radius when stationStats changes
```

---

### Issue 14 — Repo Hygiene

**Files:** `.gitignore`, repo root  
**Problem:** `node_modules/` and `*.Zone.Identifier` files tracked in git.  
**Impact:** Noisy diffs; unprofessional first impression for reviewers.

**Fix:**
```gitignore
node_modules/
*.Zone.Identifier
__pycache__/
*.pyc
.env
```
Run `git rm -r --cached node_modules/` to remove already-tracked files.

---

## 3. Architecture Upgrade Roadmap

```
Stage A ──► Stage B ──► Stage C ──► Stage D ──► Stage E
(Correctness) (Split)  (Event-Driven) (Analytics) (Polish)
```

### Stage A — Correctness Foundation (1–2 weeks)
- Typed `DateTime` schema
- Deterministic batch ingestion
- Unified error contracts (`schemas.py`, `exceptions.py`)
- Alembic migrations
- Smoke tests

### Stage B — Service Split (1 week)
- Dedicated `worker.py` ingestion process
- `api-server` process (read-only + WS later)
- Shared config module
- Health checks: `/health/live`, `/health/ready`

### Stage C — Event-Driven Core (1–2 weeks)
- Redis current-state store + Redis Streams event log
- Worker emits state-change events on meaningful diffs
- API subscribes to stream and broadcasts via WebSocket
- Frontend receives updates without polling or page refresh

### Stage D — Analytics Pipeline (1 week)
- `trip_events` table for durable event history
- `daily_summary` rollup job (scheduled)
- Materialized views for heavy queries (`worst-lines`, `by-hour`)

### Stage E — Production Polish (ongoing)
- Prometheus metrics dashboard
- Alerting on ingestion lag / error rate spikes
- Load test report
- Architecture diagram
- ADR docs in `docs/decisions/`

---

## 4. V2 Component Spec

### Ingestion Worker
- Poll every 15s with retries + jittered backoff
- Normalise entities; compute per-trip diff against Redis hash
- Emit only meaningful change events (no noise on unchanged trips)
- Batch-write event records to Postgres every 5–10s

### Redis State Layer
| Key | Type | Purpose |
|-----|------|---------|
| `railvision:trip:{trip_id}` | Hash | Current trip state |
| `railvision:events` | Stream | Ordered update log |
| TTL on stale trips | — | Prevent unbounded growth |

### API / WebSocket Broker
- REST endpoints served from Postgres summaries
- WS subscriptions scoped by station or line
- Consumes Redis stream and fans out to subscribed channels

### Postgres Schema (V2)
| Table | Key Columns |
|-------|------------|
| `trip_events` | `event_id`, `trip_id`, `station_id`, `line`, `event_type`, `old_delay`, `new_delay`, `event_ts`, `source_ts`, `ingested_ts` |
| `trip_snapshots` | (optional) full state snapshot per trip per cycle |
| `daily_station_summary` | `station_id`, `date`, `avg_delay`, `on_time_pct` |
| `daily_line_summary` | `line`, `date`, `avg_delay`, `on_time_pct` |

**Indexes:**
```sql
CREATE INDEX ON trip_events (station_id, event_ts DESC);
CREATE INDEX ON trip_events (line, event_ts DESC);
```

---

## 5. Implementation Checklist

Work through these in order. Do not skip ahead — each step builds on the last.

- [ ] **Step 1** — Write smoke tests (`test_api_smoke.py`, `test_services_contract.py`)
- [ ] **Step 2** — Fix batch upsert bug in `services.py`; verify `fetched == upserted`
- [ ] **Step 3** — Add `schemas.py` + `exceptions.py`; enforce typed return contract
- [ ] **Step 4** — Initialise Alembic; remove `create_all()` from app startup
- [ ] **Step 5** — Migrate timestamps to `TIMESTAMPTZ`; add unique index; backfill + deduplicate
- [ ] **Step 6** — Add `is_rail` flag; replace all `~` regex filters
- [ ] **Step 7** — Replace hardcoded `+11` offset with `timezone('Australia/Sydney', ...)`
- [ ] **Step 8** — Extract `worker.py`; remove scheduler from `main.py`; update Procfile
- [ ] **Step 9** — Decouple read endpoint from TfNSW (read from DB/Redis only)
- [ ] **Step 10** — Add `httpx` timeout + retry/backoff wrapper
- [ ] **Step 11** — Add `asyncio.Semaphore` concurrent polling in worker
- [ ] **Step 12** — Add structured logging + Prometheus `/metrics` endpoint
- [ ] **Step 13** — Fix frontend fetch error handling + stale marker state
- [ ] **Step 14** — Clean `.gitignore`; remove tracked `node_modules/`
- [ ] **Step 15** — Add Redis state layer (`redis_state.py`)
- [ ] **Step 16** — Add WebSocket manager (`ws_manager.py`) + frontend WS client
- [ ] **Step 17** — Add `trip_events` table migration + daily summary rollup job
- [ ] **Step 18** — Write `docs/architecture-v2.md` with before/after metrics, bug fixes referenced by commit