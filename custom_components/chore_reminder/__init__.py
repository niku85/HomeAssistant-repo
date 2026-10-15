"""The Chore Reminder integration."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration

from .chore import Chore, ChoreConfigEntry
from .const import CARD_FILENAME, DOMAIN, FRONTEND_URL_BASE

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.BUTTON, Platform.SENSOR]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Serve the bundled Lovelace card and load it in the frontend."""
    integration = await async_get_integration(hass, DOMAIN)
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                FRONTEND_URL_BASE,
                str(Path(__file__).parent / "frontend"),
                cache_headers=False,
            )
        ]
    )
    # The version query string busts the browser cache after an update.
    add_extra_js_url(
        hass, f"{FRONTEND_URL_BASE}/{CARD_FILENAME}?v={integration.version}"
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ChoreConfigEntry) -> bool:
    """Set up a chore from a config entry."""
    chore = Chore(hass, entry)
    await chore.async_load()
    entry.runtime_data = chore

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ChoreConfigEntry) -> bool:
    """Unload a chore."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        entry.runtime_data.async_unload()
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ChoreConfigEntry) -> None:
    """Delete the stored completion date when a chore is removed."""
    await Chore(hass, entry).async_remove()


async def _async_update_listener(hass: HomeAssistant, entry: ChoreConfigEntry) -> None:
    """Reload the chore after its options changed."""
    await hass.config_entries.async_reload(entry.entry_id)
