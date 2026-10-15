"""Pure date calculations for a repeating chore (no Home Assistant imports)."""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta

from .const import UNIT_DAYS, UNIT_MONTHS, UNIT_WEEKS


def add_interval(start: date, interval: int, unit: str) -> date:
    """Return ``start`` shifted forward by ``interval`` ``unit``s."""
    if unit == UNIT_DAYS:
        return start + timedelta(days=interval)
    if unit == UNIT_WEEKS:
        return start + timedelta(weeks=interval)
    if unit == UNIT_MONTHS:
        month_index = start.month - 1 + interval
        year = start.year + month_index // 12
        month = month_index % 12 + 1
        # Clamp e.g. Jan 31 + 1 month to Feb 28/29.
        day = min(start.day, calendar.monthrange(year, month)[1])
        return date(year, month, day)
    raise ValueError(f"Unknown interval unit: {unit}")


@dataclass(frozen=True)
class ChoreStatus:
    """Snapshot of a chore's state on a given day."""

    last_done: date
    next_due: date
    days_until: int
    period_days: int
    days_elapsed: int
    progress: float

    @property
    def overdue(self) -> bool:
        """Return True once the target date is in the past."""
        return self.days_until < 0

    @property
    def days_overdue(self) -> int:
        """Return how many days the chore is late (0 if not overdue)."""
        return max(0, -self.days_until)


def compute_status(last_done: date, next_due: date, today: date) -> ChoreStatus:
    """Compute countdown and progress between the last completion and the due date."""
    period_days = max(1, (next_due - last_done).days)
    days_elapsed = (today - last_done).days
    progress = min(100.0, max(0.0, days_elapsed / period_days * 100))
    return ChoreStatus(
        last_done=last_done,
        next_due=next_due,
        days_until=(next_due - today).days,
        period_days=period_days,
        days_elapsed=max(0, days_elapsed),
        progress=round(progress, 1),
    )
