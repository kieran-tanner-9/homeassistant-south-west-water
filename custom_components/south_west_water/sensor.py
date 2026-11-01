"""Sensor platform for South West Water."""

from __future__ import annotations

import datetime as dt
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

from .const import (
    CONF_SEWERAGE_RATE,
    CONF_SEWERAGE_STANDING_CHARGE,
    CONF_WATER_RATE,
    CONF_WATER_STANDING_CHARGE,
    DEFAULT_SEWERAGE_RATE,
    DEFAULT_SEWERAGE_STANDING_CHARGE,
    DEFAULT_WATER_RATE,
    DEFAULT_WATER_STANDING_CHARGE,
    DOMAIN,
    NAME,
)
from .coordinator import SouthWestWaterConfigEntry, SouthWestWaterCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SouthWestWaterConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up South West Water sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            SouthWestWaterUsageSensor(coordinator, entry),
            SouthWestWaterCostSensor(coordinator, entry),
            SouthWestWaterVolumetricRateSensor(coordinator, entry),
            SouthWestWaterStandingChargeSensor(coordinator, entry),
            SouthWestWaterTotalCostSensor(coordinator, entry),
        ]
    )


class SouthWestWaterBaseSensor(CoordinatorEntity[SouthWestWaterCoordinator], SensorEntity):
    """Base class for South West Water sensors."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SouthWestWaterCoordinator,
        entry: SouthWestWaterConfigEntry,
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self.entry = entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=NAME,
            manufacturer=NAME,
            model="Smart meter",
        )

    @property
    def water_rate(self) -> float:
        """Return the configured water supply rate."""
        return float(self.entry.options.get(CONF_WATER_RATE, DEFAULT_WATER_RATE))

    @property
    def sewerage_rate(self) -> float:
        """Return the configured sewerage rate."""
        return float(self.entry.options.get(CONF_SEWERAGE_RATE, DEFAULT_SEWERAGE_RATE))

    @property
    def water_standing_charge(self) -> float:
        """Return the configured water standing charge per day."""
        return float(
            self.entry.options.get(CONF_WATER_STANDING_CHARGE, DEFAULT_WATER_STANDING_CHARGE)
        )

    @property
    def sewerage_standing_charge(self) -> float:
        """Return the configured sewerage standing charge per day."""
        return float(
            self.entry.options.get(CONF_SEWERAGE_STANDING_CHARGE, DEFAULT_SEWERAGE_STANDING_CHARGE)
        )

    @property
    def currency(self) -> str:
        """Return Home Assistant's configured currency."""
        return self.hass.config.currency or "GBP"


class SouthWestWaterUsageSensor(SouthWestWaterBaseSensor):
    """Cumulative water usage, suitable for the Energy dashboard."""

    _attr_translation_key = "water_usage"
    _attr_device_class = SensorDeviceClass.WATER
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS
    _attr_suggested_display_precision = 3

    def __init__(
        self, coordinator: SouthWestWaterCoordinator, entry: SouthWestWaterConfigEntry
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_total_usage"

    @property
    def native_value(self) -> float:
        """Return the cumulative usage in m³."""
        return self.coordinator.data.total_usage_m3

    @property
    def extra_state_attributes(self) -> Mapping[str, Any]:
        """Return when the utility last took a reading."""
        latest = self.coordinator.data.latest_reading
        return {"last_reading": latest.isoformat() if latest else None}


class SouthWestWaterCostSensor(SouthWestWaterBaseSensor):
    """Cumulative volumetric cost year-to-date, suitable for the Energy dashboard."""

    _attr_translation_key = "water_cost"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_suggested_display_precision = 2

    def __init__(
        self, coordinator: SouthWestWaterCoordinator, entry: SouthWestWaterConfigEntry
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_water_cost"

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the currency unit."""
        return self.currency

    @property
    def native_value(self) -> float:
        """Return the cumulative volumetric cost in currency units."""
        combined_rate = self.water_rate + self.sewerage_rate
        return round(self.coordinator.data.total_usage_m3 * combined_rate, 2)


class SouthWestWaterVolumetricRateSensor(SouthWestWaterBaseSensor):
    """Current combined volumetric rate per cubic metre."""

    _attr_translation_key = "volumetric_rate"
    _attr_suggested_display_precision = 4

    def __init__(
        self, coordinator: SouthWestWaterCoordinator, entry: SouthWestWaterConfigEntry
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_volumetric_rate"

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return f"{self.currency}/m³"

    @property
    def native_value(self) -> float:
        """Return the combined volumetric rate."""
        return round(self.water_rate + self.sewerage_rate, 4)


class SouthWestWaterStandingChargeSensor(SouthWestWaterBaseSensor):
    """Cumulative standing charge year-to-date."""

    _attr_translation_key = "standing_charge"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_suggested_display_precision = 2

    def __init__(
        self, coordinator: SouthWestWaterCoordinator, entry: SouthWestWaterConfigEntry
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_standing_charge"

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the currency unit."""
        return self.currency

    @property
    def native_value(self) -> float:
        """Return the standing charge accumulated year-to-date."""
        days = dt.datetime.now(dt.UTC).timetuple().tm_yday
        daily_charge = self.water_standing_charge + self.sewerage_standing_charge
        return round(days * daily_charge, 2)


class SouthWestWaterTotalCostSensor(SouthWestWaterBaseSensor):
    """Total estimated water bill year-to-date (volumetric usage + standing charges)."""

    _attr_translation_key = "total_cost"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_suggested_display_precision = 2

    def __init__(
        self, coordinator: SouthWestWaterCoordinator, entry: SouthWestWaterConfigEntry
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_total_cost"

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the currency unit."""
        return self.currency

    @property
    def native_value(self) -> float:
        """Return the total water cost YTD."""
        combined_rate = self.water_rate + self.sewerage_rate
        usage_cost = self.coordinator.data.total_usage_m3 * combined_rate
        days = dt.datetime.now(dt.UTC).timetuple().tm_yday
        standing_charges = days * (self.water_standing_charge + self.sewerage_standing_charge)
        return round(usage_cost + standing_charges, 2)
