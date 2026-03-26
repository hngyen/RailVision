from prometheus_client import Counter, Histogram

poll_duration_seconds = Histogram(
    "railvision_poll_duration_seconds",
    "Time spent fetching and persisting departures for one stop",
    ["stop_id"],
)

upstream_errors_total = Counter(
    "railvision_upstream_errors_total",
    "Number of non-200 or network-error responses from TfNSW",
    ["stop_id"],
)

events_ingested_total = Counter(
    "railvision_events_ingested_total",
    "Number of departure rows upserted into the database",
    ["stop_id"],
)

db_write_duration_seconds = Histogram(
    "railvision_db_write_duration_seconds",
    "Time spent executing the batch upsert for one stop",
    ["stop_id"],
)
