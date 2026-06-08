from datetime import datetime, timedelta, timezone

from email_digest.timewindow import (
    DEFAULT_LOOKBACK_HOURS,
    MAX_LOOKBACK_HOURS,
    compute_lookback,
    format_hours,
    get_lookback_window,
    read_last_run,
    save_last_run,
)

UTC = timezone.utc
NOW = datetime(2026, 6, 8, 12, 0, tzinfo=UTC)


def test_format_hours_under_48_rounds_to_hours():
    assert format_hours(6) == "6h"
    assert format_hours(23.4) == "23h"
    assert format_hours(47) == "47h"


def test_format_hours_48_or_more_rounds_to_days():
    assert format_hours(48) == "2 days"
    assert format_hours(168) == "7 days"


def test_compute_lookback_no_last_run_uses_default():
    after_ts, hours = compute_lookback(NOW, None)
    assert hours == float(DEFAULT_LOOKBACK_HOURS)
    assert after_ts == int((NOW - timedelta(hours=DEFAULT_LOOKBACK_HOURS)).timestamp())


def test_compute_lookback_uses_time_since_last_run():
    last = NOW - timedelta(hours=5)
    _, hours = compute_lookback(NOW, int(last.timestamp()))
    assert round(hours) == 5


def test_compute_lookback_caps_at_max():
    last = NOW - timedelta(hours=1000)
    _, hours = compute_lookback(NOW, int(last.timestamp()))
    assert hours == float(MAX_LOOKBACK_HOURS)


def test_read_last_run_missing_returns_none(tmp_path):
    assert read_last_run(tmp_path / "nope") is None


def test_read_last_run_corrupt_returns_none(tmp_path):
    p = tmp_path / ".last_run"
    p.write_text("garbage")
    assert read_last_run(p) is None


def test_save_then_read_roundtrip(tmp_path):
    p = tmp_path / ".last_run"
    save_last_run(p, NOW)
    assert read_last_run(p) == int(NOW.timestamp())


def test_get_lookback_window_uses_saved_run(tmp_path):
    p = tmp_path / ".last_run"
    save_last_run(p, NOW - timedelta(hours=3))
    _, hours = get_lookback_window(p, NOW)
    assert round(hours) == 3
