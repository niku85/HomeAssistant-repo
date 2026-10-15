"""Date platform: view and change when a chore is due next."""

from __future__ import annotations

from datetime import date

from homeassistant.components.date import DateEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .chore import Chore, ChoreConfigEntry
from .entity import ChoreEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ChoreConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the next due date entity."""
    async_add_entities([ChoreNextDueDate(entry.runtime_data)])


class ChoreNextDueDate(ChoreEntity, DateEntity):
    """The date the chore is due next; editable to correct the schedule."""

    _attr_translation_key = "next_due"

    def __init__(self, chore: Chore) -> None:
        """Initialize the date entity."""
        super().__init__(chore, "next_due")

    @property
    def native_value(self) -> date:
        """Return the next due date."""
        return self.chore.next_due

    async def async_set_value(self, value: date) -> None:
        """Change the next due date."""
        await self.chore.async_set_next_due(value)
