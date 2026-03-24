# Foundation Baseline (Prep Pass)

This repo now has a lightweight prep layer so you can iterate safely:

- `backend/tests/` gives you a small regression harness.
- `backend/alembic/` establishes migration scaffolding.
- `backend/scripts/baseline_metrics.py` captures before/after metrics snapshots.

## 1) Install dependencies

```bash
cd backend
pip install -r requirements.txt
```

## 2) Run baseline tests

```bash
cd backend
pytest -q
```

Notes:
- Two tests are intentionally marked `xfail` for known current bugs.
- The app scheduler is disabled during tests using `RAILVISION_ENABLE_SCHEDULER=0`.

## 3) Check migration setup

```bash
cd backend
alembic current
alembic history
```

Create your first real migration when ready:

```bash
cd backend
alembic revision -m "describe schema change"
alembic upgrade head
```

## 4) Capture baseline metrics

DB-only snapshot:

```bash
cd backend
python scripts/baseline_metrics.py --output ../docs/metrics/baseline_db.json
```

DB + API latency snapshot:

```bash
cd backend
python scripts/baseline_metrics.py \
  --api-base http://localhost:8000 \
  --requests-per-endpoint 10 \
  --output ../docs/metrics/baseline_full.json
```

Key fields in output:
- `duplicate_key_groups`
- `duplicate_extra_rows`
- `freshness_lag_seconds`
- endpoint `p50_ms` / `p95_ms` and status counts

Repeat this after each major fix so you can build concrete impact statements.
