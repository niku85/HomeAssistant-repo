"""Constants for the Chore Reminder integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "chore_reminder"

CONF_START_DATE: Final = "start_date"
CONF_INTERVAL: Final = "interval"
CONF_INTERVAL_UNIT: Final = "interval_unit"

UNIT_DAYS: Final = "days"
UNIT_WEEKS: Final = "weeks"
UNIT_MONTHS: Final = "months"
INTERVAL_UNITS: Final = [UNIT_DAYS, UNIT_WEEKS, UNIT_MONTHS]

DEFAULT_INTERVAL: Final = 7
DEFAULT_INTERVAL_UNIT: Final = UNIT_DAYS

STORAGE_VERSION: Final = 1

SERVICE_MARK_DONE: Final = "mark_done"

ATTR_CHORE_NAME: Final = "chore_name"
ATTR_START_DATE: Final = "start_date"
ATTR_LAST_DONE: Final = "last_done"
ATTR_NEXT_DUE: Final = "next_due"
ATTR_INTERVAL: Final = "interval"
ATTR_INTERVAL_UNIT: Final = "interval_unit"
ATTR_PERIOD_DAYS: Final = "period_days"
ATTR_DAYS_ELAPSED: Final = "days_elapsed"
ATTR_PROGRESS: Final = "progress"
ATTR_OVERDUE: Final = "overdue"
ATTR_DAYS_OVERDUE: Final = "days_overdue"

# URL under which the bundled Lovelace card is served.
FRONTEND_URL_BASE: Final = f"/{DOMAIN}"
CARD_FILENAME: Final = "chore-reminder-card.js"
