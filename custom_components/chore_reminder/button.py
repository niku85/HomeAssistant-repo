"""Button platform: mark a chore as done."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .chore import Chore, ChoreConfigEntry
from .entity import ChoreEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ChoreConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the mark-done button."""
    async_add_entities([ChoreMarkDoneButton(entry.runtime_data)])


class ChoreMarkDoneButton(ChoreEntity, ButtonEntity):
    """Restart the chore countdown from today."""

    _attr_translation_key = "mark_done"

    def __init__(self, chore: Chore) -> None:
        """Initialize the button."""
        super().__init__(chore, "mark_done")

    async def async_press(self) -> None:
        """Mark the chore as done."""
        await self.chore.async_mark_done()
