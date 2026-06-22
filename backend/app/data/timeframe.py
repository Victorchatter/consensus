"""
Canonical timeframe vocabulary.

The legacy code let each feeder invent its own timeframe strings and even
collided "1m" (one minute) with a month bucket. Everything that loads or
validates bars now agrees on the strings and bar-spacing defined here.
"""
from __future__ import annotations

# Canonical timeframe -> nominal spacing in seconds.
# NOTE: deliberately no month/"1mo" here — intraday consensus only needs
# minute-to-week buckets, and "1m" unambiguously means one minute.
TIMEFRAME_SECONDS: dict[str, int] = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
    "1w": 604800,
}

INTRADAY = {"1m", "5m", "15m", "30m", "1h", "4h"}


def tf_seconds(timeframe: str) -> int:
    """Nominal spacing of a timeframe in seconds. Raises on unknown input."""
    try:
        return TIMEFRAME_SECONDS[timeframe]
    except KeyError:
        raise ValueError(
            f"Unknown timeframe {timeframe!r}; expected one of {sorted(TIMEFRAME_SECONDS)}"
        )


def is_intraday(timeframe: str) -> bool:
    return timeframe in INTRADAY
