"""Async client for the (undocumented) South West Water My Account web API."""

from __future__ import annotations

import datetime as dt
import json
import logging
import math
from dataclasses import dataclass
from http import HTTPStatus
from typing import Any, Final

import aiohttp

from .exceptions import (
    SouthWestWaterAuthError,
    SouthWestWaterConnectionError,
    SouthWestWaterResponseError,
    SWWApiError,
)

_LOGGER = logging.getLogger(__name__)

BASE_URL: Final = "https://myaccountwebapi.southwestwater.co.uk/api"
LOGIN_PATH: Final = "/SwwAuthenticate"
USAGE_PATH: Final = "/SwwSmartMeter/Get"

REQUEST_TIMEOUT: Final = aiohttp.ClientTimeout(total=30)
LOGIN_OK_OUTCOME: Final = 1
DEFAULT_HEADERS: Final = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) HomeAssistant-SouthWestWater",
    "Accept": "application/json, text/plain, */*",
}
MIN_READING_DATETIME: Final = dt.datetime(2000, 1, 1, tzinfo=dt.UTC)


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
        last_good_usage: MeterUsage | None = None,
    ) -> None:
        """Initialise the client."""
        self._session = session
        self._username = username
        self._password = password
        self._meter_ref = meter_ref
        self._authenticated = False
        self._last_good_usage = last_good_usage

    @property
    def last_good_usage(self) -> MeterUsage | None:
        """Return the last validated usage reading."""
        return self._last_good_usage

    @last_good_usage.setter
    def last_good_usage(self, value: MeterUsage | None) -> None:
        """Set the last validated usage reading."""
        self._last_good_usage = value

    def _clear_cookies(self) -> None:
        """Clear the session cookie jar to prevent stale session cookies."""
        cookie_jar = getattr(self._session, "cookie_jar", None)
        if cookie_jar is not None and hasattr(cookie_jar, "clear"):
            cookie_jar.clear()

    async def async_login(self) -> None:
        """Authenticate, raising SouthWestWaterAuthError if rejected.

        The configured username can be either a My Account username or an email
        address; as on the website, it is sent as both ``userId`` and ``email``.
        """
        self._clear_cookies()
        _LOGGER.debug("Logging in to South West Water API (fresh session)")
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
        # Always log in freshly with a cleared cookie jar for each usage refresh.
        await self.async_login()

        _LOGGER.debug(
            "South West Water poll date window: start=%s, end=%s, interval=%s",
            start.isoformat(),
            end.isoformat(),
            interval,
        )
        payload = {
            "meterRef": self._meter_ref_payload(),
            "startDateTime": start.astimezone(dt.UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "endDateTime": end.astimezone(dt.UTC).strftime("%Y-%m-%dT%H:%M:%S.999Z"),
            "interval": interval,
        }
        status, data = await self._post(USAGE_PATH, payload)
        keys = list(data.keys()) if isinstance(data, dict) else None
        _LOGGER.debug("South West Water usage response: status=%s, keys=%s", status, keys)

        if status in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
            # Session expired or rejected: re-authenticate freshly and retry once.
            _LOGGER.debug("Usage session rejected (%s); re-authenticating and retrying", status)
            await self.async_login()
            status, data = await self._post(USAGE_PATH, payload)
            keys = list(data.keys()) if isinstance(data, dict) else None
            _LOGGER.debug("South West Water retry response: status=%s, keys=%s", status, keys)

        if status in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
            raise SouthWestWaterAuthError("Session rejected after re-login")
        if status != HTTPStatus.OK:
            raise SWWApiError(f"Unexpected usage response status ({status})")
        if not isinstance(data, dict):
            raise SWWApiError(f"Unexpected usage response body: {type(data).__name__}")

        # 1. Validate totalUsage
        raw_total = data.get("totalUsage")
        if raw_total is None or isinstance(raw_total, bool):
            raise SWWApiError("Usage response missing or null totalUsage")
        try:
            total = float(raw_total)
        except (ValueError, TypeError) as err:
            raise SWWApiError(
                f"Usage response totalUsage is not a valid number: {raw_total!r}"
            ) from err

        if math.isnan(total) or math.isinf(total):
            raise SWWApiError(f"Usage response totalUsage is not finite: {total}")

        # 2. Validate latestReadingDateTime
        raw_reading = data.get("latestReadingDateTime")
        if not raw_reading:
            raise SWWApiError("Usage response missing latestReadingDateTime")
        latest_reading = _parse_timestamp(raw_reading)
        if latest_reading is None or latest_reading < MIN_READING_DATETIME:
            raise SWWApiError(
                f"Usage response latestReadingDateTime invalid or before 2000: {raw_reading!r}"
            )

        # 3. Check against last good value
        if self._last_good_usage is not None:
            last_total = self._last_good_usage.total_usage_m3
            last_reading = self._last_good_usage.latest_reading
            last_year = last_reading.year if last_reading else None

            is_rollover = False
            if last_year is not None:
                if latest_reading.year > last_year or start.year > last_year:
                    is_rollover = True

            if total < last_total and not is_rollover:
                raise SWWApiError(
                    f"Total usage decreased from {last_total} to {total} without a year rollover"
                )

        _LOGGER.debug(
            "South West Water poll parsed: total_usage_m3=%.3f, latest_reading=%s",
            total,
            latest_reading.isoformat(),
        )

        usage = MeterUsage(total, latest_reading)
        self._last_good_usage = usage
        return usage

    async def async_get_year_to_date(self, now: dt.datetime | None = None) -> MeterUsage:
        """Return usage from 1 January (UTC) of the current year until now."""
        now = now or dt.datetime.now(dt.UTC)
        start = dt.datetime(now.year, 1, 1, tzinfo=dt.UTC)
        end = now.replace(hour=23, minute=59, second=59)
        return await self.async_get_usage(start, end)

    def _meter_ref_payload(self) -> int | str:
        """Return the meter reference as the API expects it (a JSON number)."""
        return int(self._meter_ref) if self._meter_ref.isdigit() else self._meter_ref

    async def _post(self, path: str, payload: dict[str, Any]) -> tuple[int, Any]:
        """POST JSON and return (status, parsed body or None)."""
        try:
            async with self._session.post(
                f"{BASE_URL}{path}",
                json=payload,
                headers=DEFAULT_HEADERS,
                timeout=REQUEST_TIMEOUT,
            ) as resp:
                text = await resp.text()
                if resp.status >= HTTPStatus.BAD_REQUEST:
                    # Never includes the request payload, so no credentials.
                    _LOGGER.debug("POST %s returned HTTP %s: %.300s", path, resp.status, text)
                try:
                    body = json.loads(text)
                except ValueError:
                    body = None
                return resp.status, body
        except (TimeoutError, aiohttp.ClientError) as err:
            raise SouthWestWaterConnectionError("Cannot reach South West Water") from err
