"""Config flow tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.south_west_water.const import (
    CONF_SEWERAGE_RATE,
    CONF_SEWERAGE_STANDING_CHARGE,
    CONF_WATER_RATE,
    CONF_WATER_STANDING_CHARGE,
    DOMAIN,
)
from custom_components.south_west_water.exceptions import (
    SouthWestWaterAuthError,
    SouthWestWaterConnectionError,
    SouthWestWaterResponseError,
)

from .conftest import FAKE_DATA

FAKE_TARIFFS = {
    CONF_WATER_RATE: 2.7129,
    CONF_SEWERAGE_RATE: 3.8440,
    CONF_WATER_STANDING_CHARGE: 0.1630,
    CONF_SEWERAGE_STANDING_CHARGE: 0.2073,
}


async def test_user_flow_creates_entry(hass: HomeAssistant, mock_client: AsyncMock) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], FAKE_DATA)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "tariffs"

    with patch("custom_components.south_west_water.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], FAKE_TARIFFS)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "South West Water"
    assert result["data"] == FAKE_DATA
    assert result["options"] == FAKE_TARIFFS


@pytest.mark.parametrize(
    ("exc", "error"),
    [
        (SouthWestWaterAuthError, "invalid_auth"),
        (SouthWestWaterConnectionError, "cannot_connect"),
        (SouthWestWaterResponseError, "unknown"),
    ],
)
async def test_user_flow_errors_then_recovers(
    hass: HomeAssistant, mock_client: AsyncMock, exc: type[Exception], error: str
) -> None:
    mock_client.async_login.side_effect = exc
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], FAKE_DATA)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}

    mock_client.async_login.side_effect = None
    result = await hass.config_entries.flow.async_configure(result["flow_id"], FAKE_DATA)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "tariffs"

    with patch("custom_components.south_west_water.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], FAKE_TARIFFS)
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_duplicate_meter_aborts(
    hass: HomeAssistant, mock_client: AsyncMock, mock_entry: MockConfigEntry
) -> None:
    mock_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], FAKE_DATA)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth_flow(
    hass: HomeAssistant, mock_client: AsyncMock, mock_entry: MockConfigEntry
) -> None:
    mock_entry.add_to_hass(hass)
    result = await mock_entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"

    mock_client.async_login.side_effect = SouthWestWaterAuthError
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PASSWORD: "wrong"}
    )
    assert result["errors"] == {"base": "invalid_auth"}

    mock_client.async_login.side_effect = None
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PASSWORD: "new-fake-password"}
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert mock_entry.data[CONF_PASSWORD] == "new-fake-password"


async def test_username_is_trimmed(hass: HomeAssistant, mock_client: AsyncMock) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**FAKE_DATA, "username": "  some.user  "}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "tariffs"

    with patch("custom_components.south_west_water.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], FAKE_TARIFFS)
    assert result["data"]["username"] == "some.user"


async def test_options_flow(hass: HomeAssistant, mock_entry: MockConfigEntry) -> None:
    mock_entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(mock_entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    new_tariffs = {
        CONF_WATER_RATE: 3.1234,
        CONF_SEWERAGE_RATE: 0.0,
        CONF_WATER_STANDING_CHARGE: 0.2000,
        CONF_SEWERAGE_STANDING_CHARGE: 0.0,
    }
    result = await hass.config_entries.options.async_configure(result["flow_id"], new_tariffs)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert mock_entry.options == new_tariffs
