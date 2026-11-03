"""Data update coordinator for South West Water."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MeterUsage, SouthWestWaterClient
from .const import DEFAULT_SCAN_INTERVAL_HOURS, DOMAIN, MAX_AUTH_FAILURES, MAX_CONSECUTIVE_FAILURES
from .exceptions import SouthWestWaterAuthError, SouthWestWaterError

_LOGGER = logging.getLogger(__name__)

type SouthWestWaterConfigEntry = ConfigEntry[SouthWestWaterCoordinator]


class SouthWestWaterCoordinator(DataUpdateCoordinator[MeterUsage]):
    """Poll the South West Water API for the latest meter total."""

    config_entry: SouthWestWaterConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: SouthWestWaterConfigEntry,
        client: SouthWestWaterClient,
    ) -> None:
        """Initialise the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(hours=DEFAULT_SCAN_INTERVAL_HOURS),
        )
        self.client = client
        self.consecutive_failures = 0
        self.consecutive_auth_failures = 0

    async def _async_update_data(self) -> MeterUsage:
        """Fetch the latest usage."""
        try:
            data = await self.client.async_get_year_to_date()
        except SouthWestWaterAuthError as err:
            self.consecutive_auth_failures += 1
            self.consecutive_failures += 1
            if self.consecutive_auth_failures >= MAX_AUTH_FAILURES or self.data is None:
                raise ConfigEntryAuthFailed("Credentials rejected") from err
            raise UpdateFailed(f"Authentication failed: {err}") from err
        except SouthWestWaterError as err:
            self.consecutive_failures += 1
            raise UpdateFailed(f"Error talking to South West Water: {err}") from err

        self.consecutive_failures = 0
        self.consecutive_auth_failures = 0
        return data

    async def _async_refresh(
        self,
        log_failures: bool = True,
        raise_on_auth_failed: bool = False,
        scheduled: bool = False,
        raise_on_entry_error: bool = False,
    ) -> None:
        """Refresh data and notify listeners when availability changes."""
        prev_failures = self.consecutive_failures
        await super()._async_refresh(
            log_failures=log_failures,
            raise_on_auth_failed=raise_on_auth_failed,
            scheduled=scheduled,
            raise_on_entry_error=raise_on_entry_error,
        )
        if (
            prev_failures < MAX_CONSECUTIVE_FAILURES
            and self.consecutive_failures >= MAX_CONSECUTIVE_FAILURES
        ):
            self.async_update_listeners()
