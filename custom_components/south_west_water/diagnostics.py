"""Diagnostics for South West Water, with credentials redacted."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from .const import CONF_METER_REF
from .coordinator import SouthWestWaterConfigEntry

TO_REDACT = {CONF_USERNAME, CONF_PASSWORD, CONF_METER_REF}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: SouthWestWaterConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    usage = coordinator.data
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "options": dict(entry.options),
        "consecutive_failures": coordinator.consecutive_failures,
        "consecutive_auth_failures": coordinator.consecutive_auth_failures,
        "usage": {
            "total_usage_m3": usage.total_usage_m3,
            "latest_reading": usage.latest_reading.isoformat() if usage.latest_reading else None,
        }
        if usage
        else None,
    }
