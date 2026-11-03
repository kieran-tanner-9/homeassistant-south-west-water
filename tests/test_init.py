"""Setup, sensor and diagnostics tests."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from homeassistant.components.diagnostics import REDACTED
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.south_west_water.const import (
    CONF_SEWERAGE_RATE,
    CONF_SEWERAGE_STANDING_CHARGE,
    CONF_WATER_RATE,
    CONF_WATER_STANDING_CHARGE,
    DEFAULT_SEWERAGE_RATE,
    DEFAULT_WATER_RATE,
    DOMAIN,
)
from custom_components.south_west_water.diagnostics import async_get_config_entry_diagnostics
from custom_components.south_west_water.exceptions import (
    SouthWestWaterAuthError,
    SouthWestWaterConnectionError,
    SWWApiError,
)
from tests.conftest import FAKE_USAGE


async def test_sensor_state_and_device(
    hass: HomeAssistant, mock_client: AsyncMock, mock_entry: MockConfigEntry
) -> None:
    mock_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_entry.entry_id)
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)

    # 1. Water usage sensor
    usage_id = ent_reg.async_get_entity_id("sensor", DOMAIN, f"{mock_entry.entry_id}_total_usage")
    assert usage_id
    usage_state = hass.states.get(usage_id)
    assert usage_state is not None
    assert float(usage_state.state) == pytest.approx(12.345)
    assert usage_state.attributes["device_class"] == "water"
    assert usage_state.attributes["state_class"] == "total_increasing"
    assert usage_state.attributes["unit_of_measurement"] == "m³"
    assert usage_state.attributes["last_reading"] == "2026-06-14T23:00:00+00:00"

    # 2. Water cost sensor
    cost_id = ent_reg.async_get_entity_id("sensor", DOMAIN, f"{mock_entry.entry_id}_water_cost")
    assert cost_id
    cost_state = hass.states.get(cost_id)
    assert cost_state is not None
    expected_cost = round(12.345 * (DEFAULT_WATER_RATE + DEFAULT_SEWERAGE_RATE), 2)
    assert float(cost_state.state) == pytest.approx(expected_cost)
    assert cost_state.attributes["device_class"] == "monetary"
    assert cost_state.attributes["state_class"] == "total_increasing"

    # 3. Volumetric rate sensor
    rate_id = ent_reg.async_get_entity_id(
        "sensor", DOMAIN, f"{mock_entry.entry_id}_volumetric_rate"
    )
    assert rate_id
    rate_state = hass.states.get(rate_id)
    assert rate_state is not None
    assert float(rate_state.state) == pytest.approx(
        round(DEFAULT_WATER_RATE + DEFAULT_SEWERAGE_RATE, 4)
    )

    # 4. Standing charge sensor
    sc_id = ent_reg.async_get_entity_id("sensor", DOMAIN, f"{mock_entry.entry_id}_standing_charge")
    assert sc_id
    sc_state = hass.states.get(sc_id)
    assert sc_state is not None
    assert float(sc_state.state) > 0
    assert sc_state.attributes["device_class"] == "monetary"

    # 5. Total cost sensor
    total_id = ent_reg.async_get_entity_id("sensor", DOMAIN, f"{mock_entry.entry_id}_total_cost")
    assert total_id
    total_state = hass.states.get(total_id)
    assert total_state is not None
    assert float(total_state.state) == pytest.approx(
        round(float(cost_state.state) + float(sc_state.state), 2), abs=0.02
    )

    assert dr.async_entries_for_config_entry(dr.async_get(hass), mock_entry.entry_id)


async def test_options_update_reloads_entry(
    hass: HomeAssistant, mock_client: AsyncMock, mock_entry: MockConfigEntry
) -> None:
    mock_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_entry.entry_id)
    await hass.async_block_till_done()

    # Update options to custom zero-sewerage rate
    hass.config_entries.async_update_entry(
        mock_entry,
        options={
            CONF_WATER_RATE: 2.5000,
            CONF_SEWERAGE_RATE: 0.0,
            CONF_WATER_STANDING_CHARGE: 0.1500,
            CONF_SEWERAGE_STANDING_CHARGE: 0.0,
        },
    )
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)
    cost_id = ent_reg.async_get_entity_id("sensor", DOMAIN, f"{mock_entry.entry_id}_water_cost")
    cost_state = hass.states.get(cost_id)
    assert cost_state is not None
    # 12.345 * 2.5 = 30.86
    assert float(cost_state.state) == pytest.approx(30.86)


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
    assert isinstance(result["options"], dict)
    assert result["consecutive_failures"] == 0
    assert result["consecutive_auth_failures"] == 0


async def test_sensor_keeps_last_good_data_on_transient_failure(
    hass: HomeAssistant, mock_client: AsyncMock, mock_entry: MockConfigEntry
) -> None:
    mock_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_entry.entry_id)
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)
    usage_id = ent_reg.async_get_entity_id("sensor", DOMAIN, f"{mock_entry.entry_id}_total_usage")
    assert usage_id
    assert float(hass.states.get(usage_id).state) == pytest.approx(12.345)

    coordinator = mock_entry.runtime_data
    mock_client.async_get_year_to_date.side_effect = SWWApiError("Empty response")
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert not coordinator.last_update_success
    assert coordinator.consecutive_failures == 1
    usage_state = hass.states.get(usage_id)
    assert usage_state is not None
    assert usage_state.state != "0"
    assert usage_state.state != "0.0"
    assert float(usage_state.state) == pytest.approx(12.345)


async def test_sensor_unavailable_after_max_consecutive_failures(
    hass: HomeAssistant, mock_client: AsyncMock, mock_entry: MockConfigEntry
) -> None:
    mock_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_entry.entry_id)
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)
    usage_id = ent_reg.async_get_entity_id("sensor", DOMAIN, f"{mock_entry.entry_id}_total_usage")
    assert usage_id

    coordinator = mock_entry.runtime_data
    mock_client.async_get_year_to_date.side_effect = SWWApiError("Empty response")

    # 1st failure: remains available with last good value
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get(usage_id).state == "12.345"

    # 2nd failure: remains available with last good value
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get(usage_id).state == "12.345"

    # 3rd failure: becomes unavailable
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get(usage_id).state == "unavailable"

    # Next update succeeds: recovers
    mock_client.async_get_year_to_date.side_effect = None
    mock_client.async_get_year_to_date.return_value = FAKE_USAGE
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get(usage_id).state == "12.345"
    assert coordinator.consecutive_failures == 0


async def test_repeated_auth_failures_trigger_reauth(
    hass: HomeAssistant, mock_client: AsyncMock, mock_entry: MockConfigEntry
) -> None:
    mock_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_entry.runtime_data
    mock_client.async_get_year_to_date.side_effect = SouthWestWaterAuthError("Token expired")

    # 1st auth failure: coordinator fails update, does not trigger reauth immediately
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert not any(hass.config_entries.flow.async_progress_by_handler(DOMAIN))

    # 2nd auth failure: still update failure
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert not any(hass.config_entries.flow.async_progress_by_handler(DOMAIN))

    # 3rd auth failure: triggers reauth flow
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert any(hass.config_entries.flow.async_progress_by_handler(DOMAIN))
