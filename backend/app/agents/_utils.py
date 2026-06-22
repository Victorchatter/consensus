"""Small agent utilities — JSON-safe serialization, etc."""
from __future__ import annotations

import datetime as dt
from typing import Any


def json_safe(obj: Any) -> Any:
    """Recursively convert datetime/date objects to ISO strings for JSON storage."""
    if isinstance(obj, dt.datetime):
        return obj.isoformat()
    if isinstance(obj, dt.date):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [json_safe(v) for v in obj]
    if isinstance(obj, tuple):
        return [json_safe(v) for v in obj]
    return obj
