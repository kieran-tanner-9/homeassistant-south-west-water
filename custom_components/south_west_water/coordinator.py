"""Data update coordinator for South West Water."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MeterUsage, SouthWestWaterClient
from .const import DEFAULT_SCAN_INTERVAL_HOURS, DOMAIN
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

    async def _async_update_data(self) -> MeterUsage:
        """Fetch the latest usage."""
        try:
            return await self.client.async_get_year_to_date()
        except SouthWestWaterAuthError as err:
            raise ConfigEntryAuthFailed("Credentials rejected") from err
        except SouthWestWaterError as err:
            raise UpdateFailed(f"Error talking to South West Water: {err}") from err
