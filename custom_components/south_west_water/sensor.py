"""Sensor platform for South West Water."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NAME
from .coordinator import SouthWestWaterConfigEntry, SouthWestWaterCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SouthWestWaterConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the water meter sensor."""
    async_add_entities([SouthWestWaterUsageSensor(entry.runtime_data, entry)])


class SouthWestWaterUsageSensor(CoordinatorEntity[SouthWestWaterCoordinator], SensorEntity):
    """Cumulative water usage, suitable for the Energy dashboard."""

    _attr_has_entity_name = True
    _attr_translation_key = "water_usage"
    _attr_device_class = SensorDeviceClass.WATER
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS
    _attr_suggested_display_precision = 3

    def __init__(
        self, coordinator: SouthWestWaterCoordinator, entry: SouthWestWaterConfigEntry
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_total_usage"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=NAME,
            manufacturer=NAME,
            model="Smart meter",
        )

    @property
    def native_value(self) -> float:
        """Return the cumulative usage in m³."""
        return self.coordinator.data.total_usage_m3

    @property
    def extra_state_attributes(self) -> Mapping[str, Any]:
        """Return when the utility last took a reading."""
        latest = self.coordinator.data.latest_reading
        return {"last_reading": latest.isoformat() if latest else None}
