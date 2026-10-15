"""Integration tests for Chore Reminder."""

from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    MockModule,
    async_fire_time_changed,
    mock_integration,
)

from custom_components.chore_reminder.const import (
    CONF_INTERVAL,
    CONF_INTERVAL_UNIT,
    CONF_START_DATE,
    DOMAIN,
)

SENSOR = "sensor.water_plants"
OVERDUE = "binary_sensor.water_plants_overdue"
BUTTON = "button.water_plants_mark_done"


@pytest.fixture(autouse=True)
def mock_frontend(hass: HomeAssistant):
    """Stub the frontend; its compiled assets are not installed in tests."""
    mock_integration(hass, MockModule("frontend"))
    with patch("custom_components.chore_reminder.add_extra_js_url") as mock_add:
        yield mock_add


async def test_config_flow(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: " Water plants ",
            CONF_START_DATE: "2026-10-01",
            CONF_INTERVAL: 3.0,
            CONF_INTERVAL_UNIT: "days",
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Water plants"
    assert result["data"][CONF_INTERVAL] == 3
    await hass.async_block_till_done()

    # A second chore with the same name is rejected.
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Water plants",
            CONF_START_DATE: "2026-10-01",
            CONF_INTERVAL: 3,
            CONF_INTERVAL_UNIT: "days",
        },
    )
    assert result["type"] is FlowResultType.ABORT


async def _setup(hass: HomeAssistant, start: str = "2026-10-01") -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Water plants",
        data={
            CONF_NAME: "Water plants",
            CONF_START_DATE: start,
            CONF_INTERVAL: 10,
            CONF_INTERVAL_UNIT: "days",
        },
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_countdown_overdue_and_mark_done(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-10-05 12:00:00")
    await _setup(hass)

    state = hass.states.get(SENSOR)
    assert state.state == "6"
    assert state.attributes["next_due"] == "2026-10-11"
    assert state.attributes["progress"] == 40.0
    assert hass.states.get(OVERDUE).state == "off"

    # Two days past the target date; the midnight tick refreshes the state.
    freezer.move_to("2026-10-13 00:00:01-07:00")  # local midnight (US/Pacific)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    state = hass.states.get(SENSOR)
    assert state.state == "-2"
    assert state.attributes["overdue"] is True
    assert state.attributes["days_overdue"] == 2
    assert hass.states.get(OVERDUE).state == "on"

    await hass.services.async_call(
        DOMAIN, "mark_done", {"entity_id": SENSOR}, blocking=True
    )
    state = hass.states.get(SENSOR)
    assert state.state == "10"
    assert state.attributes["last_done"] == "2026-10-13"
    assert state.attributes["next_due"] == "2026-10-23"
    assert hass.states.get(OVERDUE).state == "off"


async def test_button_and_persistence(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-10-20 12:00:00")
    entry = await _setup(hass)

    await hass.services.async_call(
        "button", "press", {"entity_id": BUTTON}, blocking=True
    )
    assert hass.states.get(SENSOR).attributes["last_done"] == "2026-10-20"

    # Completion date survives a reload.
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(SENSOR).attributes["last_done"] == "2026-10-20"


async def test_options_change_start_date_resets(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-10-20 12:00:00")
    entry = await _setup(hass)
    await hass.services.async_call(
        "button", "press", {"entity_id": BUTTON}, blocking=True
    )

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_START_DATE: "2026-10-18", CONF_INTERVAL: 2, CONF_INTERVAL_UNIT: "weeks"},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()

    state = hass.states.get(SENSOR)
    assert state.attributes["last_done"] == "2026-10-18"
    assert state.attributes["next_due"] == "2026-11-01"
    assert state.state == "12"


async def test_card_is_served(hass: HomeAssistant, hass_client, mock_frontend) -> None:
    await _setup(hass)
    mock_frontend.assert_called_once()
    assert mock_frontend.call_args[0][1].startswith(
        "/chore_reminder/chore-reminder-card.js?v="
    )
    client = await hass_client()
    resp = await client.get("/chore_reminder/chore-reminder-card.js")
    assert resp.status == 200
    assert "chore-reminder-card" in await resp.text()
