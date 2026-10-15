"""Runtime state of a single chore."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    CONF_INTERVAL,
    CONF_INTERVAL_UNIT,
    CONF_START_DATE,
    DEFAULT_INTERVAL_UNIT,
    DOMAIN,
    STORAGE_VERSION,
)
from .schedule import ChoreStatus, compute_status

_LOGGER = logging.getLogger(__name__)

type ChoreConfigEntry = ConfigEntry[Chore]


class Chore:
    """A repeating chore backed by a config entry.

    The configured start date is the initial "last done" date; the chore is
    due one interval later. Pressing *mark done* moves "last done" to today.
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the chore."""
        self.hass = hass
        self.entry = entry
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}"
        )
        self._last_done: date = self.start_date
        self._listeners: list[Callable[[], None]] = []
        self._unsub_midnight: CALLBACK_TYPE | None = None

    @property
    def _config(self) -> dict[str, Any]:
        return {**self.entry.data, **self.entry.options}

    @property
    def name(self) -> str:
        """Return the chore name."""
        return self.entry.title or self._config[CONF_NAME]

    @property
    def start_date(self) -> date:
        """Return the configured start date."""
        return date.fromisoformat(self._config[CONF_START_DATE])

    @property
    def interval(self) -> int:
        """Return the repeat interval."""
        return int(self._config[CONF_INTERVAL])

    @property
    def interval_unit(self) -> str:
        """Return the unit of the repeat interval."""
        return self._config.get(CONF_INTERVAL_UNIT, DEFAULT_INTERVAL_UNIT)

    @property
    def last_done(self) -> date:
        """Return the date the chore was last completed."""
        return self._last_done

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device that groups this chore's entities."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.entry.entry_id)},
            name=self.name,
            manufacturer="Chore Reminder",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def status(self) -> ChoreStatus:
        """Return the current status of the chore."""
        return compute_status(
            self._last_done, self.interval, self.interval_unit, dt_util.now().date()
        )

    async def async_load(self) -> None:
        """Restore the last completion date and start the midnight refresh."""
        stored = await self._store.async_load() or {}
        # If the start date was changed in the options, restart from it.
        if stored.get(CONF_START_DATE) == self.start_date.isoformat() and (
            last_done := stored.get("last_done")
        ):
            self._last_done = date.fromisoformat(last_done)
        else:
            self._last_done = self.start_date
            await self._async_save()

        self._unsub_midnight = async_track_time_change(
            self.hass, self._async_day_changed, hour=0, minute=0, second=1
        )

    @callback
    def async_unload(self) -> None:
        """Stop listening for date changes."""
        if self._unsub_midnight:
            self._unsub_midnight()
            self._unsub_midnight = None

    async def async_remove(self) -> None:
        """Delete persisted data."""
        await self._store.async_remove()

    async def async_mark_done(self) -> None:
        """Mark the chore as done today, restarting the countdown."""
        self._last_done = dt_util.now().date()
        _LOGGER.debug("Chore %s marked done on %s", self.name, self._last_done)
        await self._async_save()
        self._notify()

    async def _async_save(self) -> None:
        await self._store.async_save(
            {
                CONF_START_DATE: self.start_date.isoformat(),
                "last_done": self._last_done.isoformat(),
            }
        )

    @callback
    def async_add_listener(self, update_callback: Callable[[], None]) -> CALLBACK_TYPE:
        """Register a callback invoked whenever the status changes."""
        self._listeners.append(update_callback)

        @callback
        def remove_listener() -> None:
            self._listeners.remove(update_callback)

        return remove_listener

    @callback
    def _async_day_changed(self, _now: datetime) -> None:
        self._notify()

    @callback
    def _notify(self) -> None:
        for update_callback in list(self._listeners):
            update_callback()
