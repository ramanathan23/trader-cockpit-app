from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any


def parse_ts(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    text = str(value).replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S%z"):
        try:
            dt = datetime.strptime(text, fmt)
            return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
        except ValueError:
            pass
    try:
        dt = datetime.fromisoformat(str(value))
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
    except ValueError:
        return None


def json_text(data: Any) -> str:
    return json.dumps(data, default=str)


def payload(value: Any) -> Any:
    out = value
    for _ in range(2):
        if not isinstance(out, str):
            break
        try:
            out = json.loads(out)
        except json.JSONDecodeError:
            return {}
    return out or {}


def money_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0
