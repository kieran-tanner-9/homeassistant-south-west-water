"""Exceptions raised by the South West Water API client."""

from __future__ import annotations


class SouthWestWaterError(Exception):
    """Base class for all South West Water errors."""


class SouthWestWaterConnectionError(SouthWestWaterError):
    """The API could not be reached or timed out."""


class SouthWestWaterAuthError(SouthWestWaterError):
    """The credentials were rejected or the session is no longer valid."""


class SouthWestWaterResponseError(SouthWestWaterError):
    """The API answered with something unexpected."""
