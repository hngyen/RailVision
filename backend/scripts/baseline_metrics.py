#!/usr/bin/env python3
"""
Capture baseline metrics before backend refactors.

Usage examples:
  python scripts/baseline_metrics.py
  python scripts/baseline_metrics.py --api-base http://localhost:8000
  python scripts/baseline_metrics.py --api-base http://localhost:8000 --requests-per-endpoint 10 --output ../docs/metrics/baseline_v1.json
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None

    try:
        normalized = value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None

    ordered = sorted(values)
    idx = int(round((len(ordered) - 1) * p))
    return round(ordered[idx], 2)


def collect_db_metrics(db_path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "db_path": str(db_path),
        "db_exists": db_path.exists(),
    }

    if not db_path.exists():
        return result

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) AS c FROM departures")
        result["total_rows"] = cur.fetchone()["c"]

        cur.execute(
            """
            SELECT COUNT(*) AS c
            FROM (
              SELECT line, scheduled, stop_id
              FROM departures
              GROUP BY line, scheduled, stop_id
              HAVING COUNT(*) > 1
            ) t
            """
        )
        result["duplicate_key_groups"] = cur.fetchone()["c"]

        cur.execute(
            """
            SELECT COALESCE(SUM(c - 1), 0) AS c
            FROM (
              SELECT COUNT(*) AS c
              FROM departures
              GROUP BY line, scheduled, stop_id
              HAVING COUNT(*) > 1
            ) t
            """
        )
        result["duplicate_extra_rows"] = cur.fetchone()["c"]

        cur.execute("SELECT MAX(fetched_at) AS latest FROM departures")
        latest_fetched_at = cur.fetchone()["latest"]
        result["latest_fetched_at"] = latest_fetched_at

        latest_dt = parse_iso(latest_fetched_at)
        if latest_dt:
            result["freshness_lag_seconds"] = round(
                (datetime.now(timezone.utc) - latest_dt.astimezone(timezone.utc)).total_seconds(),
                2,
            )
        else:
            result["freshness_lag_seconds"] = None

        cur.execute(
            """
            SELECT stop_id, COUNT(*) AS c
            FROM departures
            GROUP BY stop_id
            ORDER BY c DESC
            LIMIT 10
            """
        )
        result["top_stops_by_rows"] = [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()

    return result


def collect_api_metrics(api_base: str, requests_per_endpoint: int, timeout: float) -> dict[str, Any]:
    endpoints = [
        "/",
        "/departures/live/200060",
        "/analytics/worst-lines?stop_id=200060",
        "/analytics/delays/by-hour?stop_id=200060",
    ]
    metrics: dict[str, Any] = {}

    for endpoint in endpoints:
        url = f"{api_base.rstrip('/')}{endpoint}"
        latencies_ms: list[float] = []
        status_counts: dict[str, int] = {}
        errors: list[str] = []

        for _ in range(requests_per_endpoint):
            start = time.perf_counter()
            try:
                response = requests.get(url, timeout=timeout)
                latency_ms = (time.perf_counter() - start) * 1000
                latencies_ms.append(latency_ms)
                key = str(response.status_code)
                status_counts[key] = status_counts.get(key, 0) + 1
            except requests.RequestException as exc:
                latency_ms = (time.perf_counter() - start) * 1000
                latencies_ms.append(latency_ms)
                errors.append(str(exc))
                status_counts["request_exception"] = status_counts.get("request_exception", 0) + 1

        metrics[endpoint] = {
            "requests": requests_per_endpoint,
            "status_counts": status_counts,
            "p50_ms": percentile(latencies_ms, 0.50),
            "p95_ms": percentile(latencies_ms, 0.95),
            "max_ms": round(max(latencies_ms), 2) if latencies_ms else None,
            "errors": errors[:5],
        }

    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture RailVision baseline metrics.")
    parser.add_argument(
        "--db-path",
        default="../data/railvision.db",
        help="Path to sqlite database file relative to backend/ (default: ../data/railvision.db)",
    )
    parser.add_argument(
        "--api-base",
        default=None,
        help="Optional API base URL for latency checks (example: http://localhost:8000)",
    )
    parser.add_argument(
        "--requests-per-endpoint",
        type=int,
        default=5,
        help="Requests to send per endpoint when --api-base is set.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=8.0,
        help="HTTP timeout seconds for endpoint checks.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional path to write JSON output.",
    )
    args = parser.parse_args()

    db_path = Path(args.db_path).resolve()
    payload: dict[str, Any] = {
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "db_metrics": collect_db_metrics(db_path),
    }

    if args.api_base:
        payload["api_metrics"] = collect_api_metrics(
            api_base=args.api_base,
            requests_per_endpoint=args.requests_per_endpoint,
            timeout=args.timeout,
        )

    rendered = json.dumps(payload, indent=2)
    print(rendered)

    if args.output:
        output_path = Path(args.output).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")
        print(f"\nSaved metrics to: {output_path}")


if __name__ == "__main__":
    main()
