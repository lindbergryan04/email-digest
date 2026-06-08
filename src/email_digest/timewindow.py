"""Lookback-window logic: how far back to pull email, and how to display it.

The core functions take their inputs explicitly (current time, last-run
timestamp) so they're deterministic and unit-testable. The only impurity --
reading the system clock -- is left to the caller (the CLI).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

DEFAULT_LOOKBACK_HOURS = 24  # first run, or when .last_run is missing/corrupt
MAX_LOOKBACK_HOURS = 168  # 7 days -- cap so a long absence doesn't pull weeks


def format_hours(hours: float) -> str:
    """Human-friendly lookback window: '6h', '23h', '2 days', '7 days'."""
    if hours < 48:
        return f"{round(hours)}h"
    return f"{round(hours / 24)} days"


def compute_lookback(
    now: datetime,
    last_run_ts: int | None = None,
    *,
    default_hours: int = DEFAULT_LOOKBACK_HOURS,
    max_hours: int = MAX_LOOKBACK_HOURS,
) -> tuple[int, float]:
    """Return ``(after_unix_ts, lookback_hours)``.

    Pure. With no usable last run, falls back to ``default_hours``; always caps
    the window at ``max_hours``.
    """
    if last_run_ts is None:
        hours = float(default_hours)
    else:
        last_run = datetime.fromtimestamp(last_run_ts, tz=timezone.utc)
        hours = (now - last_run).total_seconds() / 3600
    hours = min(hours, float(max_hours))
    after_ts = int((now - timedelta(hours=hours)).timestamp())
    return after_ts, hours


def read_last_run(path: Path) -> int | None:
    """Read a unix timestamp from ``path``; return None if missing or corrupt."""
    try:
        return int(Path(path).read_text().strip())
    except (FileNotFoundError, ValueError, OSError):
        return None


def save_last_run(path: Path, now: datetime) -> None:
    """Persist ``now`` as a unix timestamp to ``path``."""
    Path(path).write_text(str(int(now.timestamp())))


def get_lookback_window(path: Path, now: datetime) -> tuple[int, float]:
    """Combine a stored ``.last_run`` (if any) with ``now`` into a window."""
    return compute_lookback(now, read_last_run(path))
