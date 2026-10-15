"""Base entity for Chore Reminder."""

from __future__ import annotations

from homeassistant.helpers.entity import Entity

from .chore import Chore


class ChoreEntity(Entity):
    """An entity that belongs to a chore and updates with it."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, chore: Chore, key: str) -> None:
        """Initialize the entity."""
        self.chore = chore
        self._attr_unique_id = f"{chore.entry.entry_id}_{key}"
        self._attr_device_info = chore.device_info

    async def async_added_to_hass(self) -> None:
        """Subscribe to chore updates."""
        await super().async_added_to_hass()
        self.async_on_remove(self.chore.async_add_listener(self.async_write_ha_state))
