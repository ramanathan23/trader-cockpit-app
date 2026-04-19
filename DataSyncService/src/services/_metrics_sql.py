from pathlib import Path

METRICS_UPSERT_SQL: str = (
    Path(__file__).parent / "_metrics_upsert.sql"
).read_text()
