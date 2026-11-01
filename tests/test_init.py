"""Setup, sensor and diagnostics tests."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from homeassistant.components.diagnostics import REDACTED
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.south_west_water.const import DOMAIN
from custom_components.south_west_water.diagnostics import async_get_config_entry_diagnostics
from custom_components.south_west_water.exceptions import (
    SouthWestWaterAuthError,
    SouthWestWaterConnectionError,
)


async def test_sensor_state_and_device(
    hass: HomeAssistant, mock_client: AsyncMock, mock_entry: MockConfigEntry
) -> None:
    mock_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_entry.entry_id)
    await hass.async_block_till_done()

    entity_id = er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, f"{mock_entry.entry_id}_total_usage"
    )
    assert entity_id
    state = hass.states.get(entity_id)
    assert state is not None
    assert float(state.state) == pytest.approx(12.345)
    assert state.attributes["device_class"] == "water"
    assert state.attributes["state_class"] == "total_increasing"
    assert state.attributes["unit_of_measurement"] == "m³"
    assert state.attributes["last_reading"] == "2026-06-14T23:00:00+00:00"
    assert dr.async_get(hass).async_get_device(identifiers={(DOMAIN, mock_entry.entry_id)})


async def test_unload(
    hass: HomeAssistant, mock_client: AsyncMock, mock_entry: MockConfigEntry
) -> None:
    mock_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_entry.entry_id)
    await hass.config_entries.async_unload(mock_entry.entry_id)
    assert mock_entry.state is ConfigEntryState.NOT_LOADED


async def test_auth_failure_starts_reauth(
    hass: HomeAssistant, mock_client: AsyncMock, mock_entry: MockConfigEntry
) -> None:
    mock_client.async_get_year_to_date.side_effect = SouthWestWaterAuthError
    mock_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_entry.state is ConfigEntryState.SETUP_ERROR
    assert any(hass.config_entries.flow.async_progress_by_handler(DOMAIN))


async def test_connection_failure_retries(
    hass: HomeAssistant, mock_client: AsyncMock, mock_entry: MockConfigEntry
) -> None:
    mock_client.async_get_year_to_date.side_effect = SouthWestWaterConnectionError
    mock_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_entry.entry_id)
    assert mock_entry.state is ConfigEntryState.SETUP_RETRY


async def test_diagnostics_redacts_secrets(
    hass: HomeAssistant, mock_client: AsyncMock, mock_entry: MockConfigEntry
) -> None:
    mock_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_entry.entry_id)
    result = await async_get_config_entry_diagnostics(hass, mock_entry)
    assert result["entry"] == {
        "username": REDACTED,
        "password": REDACTED,
        "meter_ref": REDACTED,
    }
    assert result["usage"]["total_usage_m3"] == pytest.approx(12.345)
