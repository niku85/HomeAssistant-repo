"""Binary sensor platform: is a chore overdue."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .chore import Chore, ChoreConfigEntry
from .entity import ChoreEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ChoreConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the overdue binary sensor."""
    async_add_entities([ChoreOverdueBinarySensor(entry.runtime_data)])


class ChoreOverdueBinarySensor(ChoreEntity, BinarySensorEntity):
    """On when the target date has passed without the chore being done."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_translation_key = "overdue"

    def __init__(self, chore: Chore) -> None:
        """Initialize the binary sensor."""
        super().__init__(chore, "overdue")

    @property
    def is_on(self) -> bool:
        """Return True if the chore is overdue."""
        return self.chore.status.overdue
