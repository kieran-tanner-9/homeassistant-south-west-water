"""Constants for the South West Water integration."""

from __future__ import annotations

DOMAIN = "south_west_water"
NAME = "South West Water"

CONF_METER_REF = "meter_ref"

CONF_WATER_RATE = "water_rate"
CONF_SEWERAGE_RATE = "sewerage_rate"
CONF_WATER_STANDING_CHARGE = "water_standing_charge"
CONF_SEWERAGE_STANDING_CHARGE = "sewerage_standing_charge"

# Standard SWW metered tariffs (April 2026).
# Sewerage volumetric charge reflects the standard 90% return-to-sewer allowance.
DEFAULT_WATER_RATE = 2.7129
DEFAULT_SEWERAGE_RATE = 3.8440
DEFAULT_WATER_STANDING_CHARGE = 0.1630
DEFAULT_SEWERAGE_STANDING_CHARGE = 0.2073

DEFAULT_SCAN_INTERVAL_HOURS = 6

MAX_CONSECUTIVE_FAILURES = 3
MAX_AUTH_FAILURES = 3
