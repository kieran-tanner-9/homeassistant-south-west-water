"""Smoke test so CI has something to run from the first commit."""

from custom_components.south_west_water.const import DOMAIN


def test_domain() -> None:
    assert DOMAIN == "south_west_water"
