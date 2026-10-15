"""Config flow for Chore Reminder."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.util import dt as dt_util

from .const import (
    CONF_INTERVAL,
    CONF_INTERVAL_UNIT,
    CONF_START_DATE,
    DEFAULT_INTERVAL,
    DEFAULT_INTERVAL_UNIT,
    DOMAIN,
    INTERVAL_UNITS,
)


def _schedule_schema(defaults: dict[str, Any]) -> dict[vol.Marker, Any]:
    """Return the start date / interval part of the form."""
    return {
        vol.Required(
            CONF_START_DATE, default=defaults[CONF_START_DATE]
        ): selector.DateSelector(),
        vol.Required(
            CONF_INTERVAL, default=defaults[CONF_INTERVAL]
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=1, max=3650, step=1, mode=selector.NumberSelectorMode.BOX
            )
        ),
        vol.Required(
            CONF_INTERVAL_UNIT, default=defaults[CONF_INTERVAL_UNIT]
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=INTERVAL_UNITS,
                translation_key=CONF_INTERVAL_UNIT,
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        ),
    }


def _normalize(user_input: dict[str, Any]) -> dict[str, Any]:
    """NumberSelector returns floats; store the interval as an int."""
    return {**user_input, CONF_INTERVAL: int(user_input[CONF_INTERVAL])}


class ChoreReminderConfigFlow(ConfigFlow, domain=DOMAIN):
    """Create a new chore."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the chore name, start date and interval."""
        if user_input is not None:
            name = user_input[CONF_NAME].strip()
            self._async_abort_entries_match({CONF_NAME: name})
            return self.async_create_entry(
                title=name, data=_normalize({**user_input, CONF_NAME: name})
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME): selector.TextSelector(),
                **_schedule_schema(
                    {
                        CONF_START_DATE: dt_util.now().date().isoformat(),
                        CONF_INTERVAL: DEFAULT_INTERVAL,
                        CONF_INTERVAL_UNIT: DEFAULT_INTERVAL_UNIT,
                    }
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow."""
        return ChoreReminderOptionsFlow()


class ChoreReminderOptionsFlow(OptionsFlow):
    """Change the schedule of an existing chore."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit start date and interval."""
        if user_input is not None:
            return self.async_create_entry(data=_normalize(user_input))

        current = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(
            step_id="init", data_schema=vol.Schema(_schedule_schema(current))
        )
