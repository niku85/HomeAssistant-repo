"""Sensor platform: days until a chore is due."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .chore import Chore, ChoreConfigEntry
from .const import (
    ATTR_CHORE_NAME,
    ATTR_DAYS_ELAPSED,
    ATTR_DAYS_OVERDUE,
    ATTR_INTERVAL,
    ATTR_INTERVAL_UNIT,
    ATTR_LAST_DONE,
    ATTR_NEXT_DUE,
    ATTR_OVERDUE,
    ATTR_PERIOD_DAYS,
    ATTR_PROGRESS,
    ATTR_START_DATE,
    SERVICE_MARK_DONE,
)
from .entity import ChoreEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ChoreConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the chore sensor."""
    async_add_entities([ChoreDaysUntilSensor(entry.runtime_data)])

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(SERVICE_MARK_DONE, None, "async_mark_done")


class ChoreDaysUntilSensor(ChoreEntity, SensorEntity):
    """Number of days until the chore is due (negative when overdue)."""

    _attr_name = None  # Use the chore (device) name as the entity name.
    _attr_native_unit_of_measurement = UnitOfTime.DAYS
    _attr_suggested_display_precision = 0

    def __init__(self, chore: Chore) -> None:
        """Initialize the sensor."""
        super().__init__(chore, "days_until")

    @property
    def native_value(self) -> int:
        """Return the days until the chore is due."""
        return self.chore.status.days_until

    @property
    def icon(self) -> str:
        """Return an alert icon when overdue."""
        return "mdi:alert-circle" if self.chore.status.overdue else "mdi:broom"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the details the Lovelace card needs."""
        status = self.chore.status
        return {
            ATTR_CHORE_NAME: self.chore.name,
            ATTR_START_DATE: self.chore.start_date.isoformat(),
            ATTR_LAST_DONE: status.last_done.isoformat(),
            ATTR_NEXT_DUE: status.next_due.isoformat(),
            ATTR_INTERVAL: self.chore.interval,
            ATTR_INTERVAL_UNIT: self.chore.interval_unit,
            ATTR_PERIOD_DAYS: status.period_days,
            ATTR_DAYS_ELAPSED: status.days_elapsed,
            ATTR_PROGRESS: status.progress,
            ATTR_OVERDUE: status.overdue,
            ATTR_DAYS_OVERDUE: status.days_overdue,
        }

    async def async_mark_done(self) -> None:
        """Handle the mark_done entity service."""
        await self.chore.async_mark_done()
