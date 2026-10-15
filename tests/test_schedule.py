"""Tests for the pure date calculations."""

from datetime import date

import pytest

from custom_components.chore_reminder.schedule import add_interval, compute_status


@pytest.mark.parametrize(
    ("start", "interval", "unit", "expected"),
    [
        (date(2026, 1, 1), 3, "days", date(2026, 1, 4)),
        (date(2026, 1, 1), 2, "weeks", date(2026, 1, 15)),
        (date(2026, 1, 31), 1, "months", date(2026, 2, 28)),
        (date(2024, 1, 31), 1, "months", date(2024, 2, 29)),
        (date(2026, 11, 15), 3, "months", date(2027, 2, 15)),
    ],
)
def test_add_interval(start, interval, unit, expected) -> None:
    assert add_interval(start, interval, unit) == expected


def test_status_in_progress() -> None:
    status = compute_status(date(2026, 1, 1), date(2026, 1, 11), date(2026, 1, 4))
    assert status.next_due == date(2026, 1, 11)
    assert status.days_until == 7
    assert status.progress == 30.0
    assert not status.overdue
    assert status.days_overdue == 0


def test_status_due_today_is_not_overdue() -> None:
    status = compute_status(date(2026, 1, 1), date(2026, 1, 11), date(2026, 1, 11))
    assert status.days_until == 0
    assert status.progress == 100.0
    assert not status.overdue


def test_status_overdue() -> None:
    status = compute_status(date(2026, 1, 1), date(2026, 1, 11), date(2026, 1, 14))
    assert status.overdue
    assert status.days_overdue == 3
    assert status.progress == 100.0


def test_status_future_start() -> None:
    status = compute_status(date(2026, 2, 1), date(2026, 2, 8), date(2026, 1, 30))
    assert status.days_until == 9
    assert status.progress == 0.0
    assert status.days_elapsed == 0


def test_status_due_date_before_last_done() -> None:
    """A hand-set due date earlier than the last completion must not crash."""
    status = compute_status(date(2026, 1, 10), date(2026, 1, 5), date(2026, 1, 10))
    assert status.period_days == 1
    assert status.days_until == -5
    assert status.overdue
