"""Shared pytest fixtures."""

from __future__ import annotations

import datetime as dt
from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.south_west_water.api import MeterUsage
from custom_components.south_west_water.const import CONF_METER_REF, DOMAIN

FAKE_DATA = {
    CONF_USERNAME: "user@example.invalid",
    CONF_PASSWORD: "fake-password",
    CONF_METER_REF: "000000",
}
FAKE_USAGE = MeterUsage(12.345, dt.datetime(2026, 6, 14, 23, tzinfo=dt.UTC))


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Allow Home Assistant to load custom_components in tests."""
    yield


@pytest.fixture
def mock_client() -> Generator[AsyncMock]:
    """Patch the API client everywhere it is constructed."""
    with (
        patch("custom_components.south_west_water.SouthWestWaterClient", autospec=True) as cls,
        patch("custom_components.south_west_water.config_flow.SouthWestWaterClient", new=cls),
    ):
        client = cls.return_value
        client.async_login.return_value = None
        client.async_get_year_to_date.return_value = FAKE_USAGE
        yield client


@pytest.fixture
def mock_entry() -> MockConfigEntry:
    """Return a config entry with fake credentials."""
    return MockConfigEntry(domain=DOMAIN, data=FAKE_DATA, unique_id=FAKE_DATA[CONF_METER_REF])
