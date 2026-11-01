"""Async client for the (undocumented) South West Water My Account web API."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from http import HTTPStatus
from typing import Any, Final

import aiohttp

from .exceptions import (
    SouthWestWaterAuthError,
    SouthWestWaterConnectionError,
    SouthWestWaterResponseError,
)

BASE_URL: Final = "https://myaccountwebapi.southwestwater.co.uk/api"
LOGIN_PATH: Final = "/SwwAuthenticate"
USAGE_PATH: Final = "/SwwSmartMeter/Get"

REQUEST_TIMEOUT: Final = aiohttp.ClientTimeout(total=30)
LOGIN_OK_OUTCOME: Final = 1
DEFAULT_HEADERS: Final = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) HomeAssistant-SouthWestWater",
    "Accept": "application/json, text/plain, */*",
}


@dataclass(frozen=True, slots=True)
class MeterUsage:
    """Cumulative usage reported by the smart meter endpoint."""

    total_usage_m3: float
    latest_reading: dt.datetime | None


def _parse_timestamp(value: Any) -> dt.datetime | None:
    """Parse an ISO 8601 timestamp, returning None if absent or malformed."""
    if not isinstance(value, str):
        return None
    try:
        parsed = dt.datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.UTC)


class SouthWestWaterClient:
    """Client for the South West Water API.

    Authentication is cookie based, so pass a session dedicated to this client
    (e.g. ``async_create_clientsession``) rather than HA's shared session.
    """

    def __init__(
        self,
        session: aiohttp.ClientSession,
        username: str,
        password: str,
        meter_ref: str,
    ) -> None:
        """Initialise the client."""
        self._session = session
        self._username = username
        self._password = password
        self._meter_ref = meter_ref
        self._authenticated = False

    async def async_login(self) -> None:
        """Authenticate, raising SouthWestWaterAuthError if rejected."""
        payload = {
            "userId": self._username,
            "pwd": self._password,
            "email": self._username,
        }
        status, data = await self._post(LOGIN_PATH, payload)
        if status in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
            raise SouthWestWaterAuthError("Login rejected")
        if status != HTTPStatus.OK or not isinstance(data, dict):
            raise SouthWestWaterResponseError(f"Unexpected login response ({status})")
        if data.get("opOutcomeCode") != LOGIN_OK_OUTCOME:
            raise SouthWestWaterAuthError("Invalid username or password")
        self._authenticated = True

    async def async_get_usage(
        self,
        start: dt.datetime,
        end: dt.datetime,
        interval: str = "month",
    ) -> MeterUsage:
        """Return cumulative usage between two datetimes."""
        if not self._authenticated:
            await self.async_login()
        payload = {
            "meterRef": self._meter_ref,
            "startDateTime": start.astimezone(dt.UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "endDateTime": end.astimezone(dt.UTC).strftime("%Y-%m-%dT%H:%M:%S.999Z"),
            "interval": interval,
        }
        status, data = await self._post(USAGE_PATH, payload)
        if status in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
            # Session expired: log in once more and retry.
            self._authenticated = False
            await self.async_login()
            status, data = await self._post(USAGE_PATH, payload)
        if status in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
            raise SouthWestWaterAuthError("Session rejected after re-login")
        if status != HTTPStatus.OK or not isinstance(data, dict):
            raise SouthWestWaterResponseError(f"Unexpected usage response ({status})")
        try:
            total = float(data["totalUsage"])
        except (KeyError, TypeError, ValueError) as err:
            raise SouthWestWaterResponseError("Response has no valid totalUsage") from err
        return MeterUsage(total, _parse_timestamp(data.get("latestReadingDateTime")))

    async def async_get_year_to_date(self, now: dt.datetime | None = None) -> MeterUsage:
        """Return usage from 1 January (UTC) of the current year until now."""
        now = now or dt.datetime.now(dt.UTC)
        start = dt.datetime(now.year, 1, 1, tzinfo=dt.UTC)
        end = now.replace(hour=23, minute=59, second=59)
        return await self.async_get_usage(start, end)

    async def _post(self, path: str, payload: dict[str, Any]) -> tuple[int, Any]:
        """POST JSON and return (status, parsed body or None)."""
        try:
            async with self._session.post(
                f"{BASE_URL}{path}",
                json=payload,
                headers=DEFAULT_HEADERS,
                timeout=REQUEST_TIMEOUT,
            ) as resp:
                try:
                    body = await resp.json(content_type=None)
                except aiohttp.ContentTypeError, ValueError:
                    body = None
                return resp.status, body
        except (TimeoutError, aiohttp.ClientError) as err:
            raise SouthWestWaterConnectionError("Cannot reach South West Water") from err
