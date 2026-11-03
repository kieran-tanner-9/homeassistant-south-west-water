"""Tests for the South West Water API client (fake data only)."""

from __future__ import annotations

import datetime as dt
import json as jsonlib
from typing import Any

import aiohttp
import pytest

from custom_components.south_west_water.api import (
    BASE_URL,
    LOGIN_PATH,
    USAGE_PATH,
    SouthWestWaterClient,
)
from custom_components.south_west_water.exceptions import (
    SouthWestWaterAuthError,
    SouthWestWaterConnectionError,
    SouthWestWaterResponseError,
    SWWApiError,
)

LOGIN_URL = f"{BASE_URL}{LOGIN_PATH}"
USAGE_URL = f"{BASE_URL}{USAGE_PATH}"
NOW = dt.datetime(2026, 6, 15, 10, 30, tzinfo=dt.UTC)
LOGIN_OK = (200, {"opOutcomeCode": 1})


class FakeResponse:
    """Minimal stand-in for aiohttp.ClientResponse."""

    def __init__(self, status: int, body: Any) -> None:
        self.status = status
        self._body = body

    async def __aenter__(self) -> FakeResponse:
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    async def text(self) -> str:
        if self._body is None:
            return ""
        if isinstance(self._body, str):
            return self._body
        return jsonlib.dumps(self._body)


class FakeCookieJar:
    """Mock aiohttp cookie jar."""

    def __init__(self) -> None:
        self.clear_count = 0

    def clear(self) -> None:
        self.clear_count += 1


class FakeSession:
    """Replays queued (status, body) tuples or exceptions, recording calls."""

    def __init__(self, *queue: tuple[int, Any] | Exception) -> None:
        self._queue = list(queue)
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.cookie_jar = FakeCookieJar()

    def post(self, url: str, *, json: dict[str, Any], **_: Any) -> FakeResponse:
        self.calls.append((url, json))
        item = self._queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return FakeResponse(*item)


def make_client(*queue: tuple[int, Any] | Exception) -> tuple[SouthWestWaterClient, FakeSession]:
    session = FakeSession(*queue)
    return SouthWestWaterClient(session, "user@example.invalid", "fake-pass", "123456"), session  # type: ignore[arg-type]


async def test_login_success() -> None:
    client, _ = make_client(LOGIN_OK)
    await client.async_login()


async def test_login_bad_credentials() -> None:
    client, _ = make_client((200, {"opOutcomeCode": 0}))
    with pytest.raises(SouthWestWaterAuthError):
        await client.async_login()


async def test_login_http_401() -> None:
    client, _ = make_client((401, None))
    with pytest.raises(SouthWestWaterAuthError):
        await client.async_login()


async def test_login_server_error() -> None:
    client, _ = make_client((500, None))
    with pytest.raises(SouthWestWaterResponseError):
        await client.async_login()


async def test_usage_year_to_date() -> None:
    client, _ = make_client(
        LOGIN_OK,
        (200, {"totalUsage": "123.456", "latestReadingDateTime": "2026-06-14T23:00:00Z"}),
    )
    usage = await client.async_get_year_to_date(NOW)
    assert usage.total_usage_m3 == pytest.approx(123.456)
    assert usage.latest_reading == dt.datetime(2026, 6, 14, 23, tzinfo=dt.UTC)


async def test_usage_request_payload() -> None:
    client, session = make_client(
        LOGIN_OK,
        (200, {"totalUsage": 1, "latestReadingDateTime": "2026-06-14T23:00:00Z"}),
    )
    await client.async_get_year_to_date(NOW)
    url, body = session.calls[-1]
    assert url == USAGE_URL
    assert body["startDateTime"] == "2026-01-01T00:00:00.000Z"
    assert body["endDateTime"] == "2026-06-15T23:59:59.999Z"
    assert body["interval"] == "month"
    assert body["meterRef"] == 123456  # numeric, as the website API expects


async def test_usage_without_latest_reading() -> None:
    client, _ = make_client(LOGIN_OK, (200, {"totalUsage": 5}))
    with pytest.raises(SWWApiError):
        await client.async_get_year_to_date(NOW)


async def test_usage_reading_date_before_2000_fails() -> None:
    client, _ = make_client(
        LOGIN_OK,
        (200, {"totalUsage": 5, "latestReadingDateTime": "1999-12-31T23:59:59Z"}),
    )
    with pytest.raises(SWWApiError):
        await client.async_get_year_to_date(NOW)


async def test_usage_missing_total() -> None:
    client, _ = make_client(LOGIN_OK, (200, {"other": 1}))
    with pytest.raises(SWWApiError):
        await client.async_get_year_to_date(NOW)


async def test_usage_null_total_fails() -> None:
    client, _ = make_client(
        LOGIN_OK,
        (200, {"totalUsage": None, "latestReadingDateTime": "2026-06-14T23:00:00Z"}),
    )
    with pytest.raises(SWWApiError):
        await client.async_get_year_to_date(NOW)


async def test_usage_bool_total_fails() -> None:
    client, _ = make_client(
        LOGIN_OK,
        (200, {"totalUsage": True, "latestReadingDateTime": "2026-06-14T23:00:00Z"}),
    )
    with pytest.raises(SWWApiError):
        await client.async_get_year_to_date(NOW)


async def test_usage_nan_total_fails() -> None:
    client, _ = make_client(
        LOGIN_OK,
        (200, {"totalUsage": "NaN", "latestReadingDateTime": "2026-06-14T23:00:00Z"}),
    )
    with pytest.raises(SWWApiError):
        await client.async_get_year_to_date(NOW)


async def test_usage_non_numeric_total_fails() -> None:
    client, _ = make_client(
        LOGIN_OK,
        (200, {"totalUsage": "not-a-number", "latestReadingDateTime": "2026-06-14T23:00:00Z"}),
    )
    with pytest.raises(SWWApiError):
        await client.async_get_year_to_date(NOW)


async def test_usage_empty_body_fails() -> None:
    client, _ = make_client(LOGIN_OK, (200, ""))
    with pytest.raises(SWWApiError):
        await client.async_get_year_to_date(NOW)


async def test_usage_html_body_fails() -> None:
    client, _ = make_client(LOGIN_OK, (200, "<!DOCTYPE html><html><body>Error</body></html>"))
    with pytest.raises(SWWApiError):
        await client.async_get_year_to_date(NOW)


async def test_usage_reauthenticates_on_401() -> None:
    client, session = make_client(
        LOGIN_OK,
        (401, None),
        LOGIN_OK,
        (200, {"totalUsage": 9, "latestReadingDateTime": "2026-06-14T23:00:00Z"}),
    )
    usage = await client.async_get_year_to_date(NOW)
    assert usage.total_usage_m3 == 9
    assert [u for u, _ in session.calls].count(LOGIN_URL) == 2


async def test_usage_auth_failure_after_retry() -> None:
    client, _ = make_client(LOGIN_OK, (401, None), LOGIN_OK, (401, None))
    with pytest.raises(SouthWestWaterAuthError):
        await client.async_get_year_to_date(NOW)


async def test_usage_clears_cookie_jar_on_login() -> None:
    client, session = make_client(LOGIN_OK)
    await client.async_login()
    assert session.cookie_jar.clear_count == 1


async def test_usage_second_call_default_empty_payload_fails() -> None:
    """Second call returning default .NET payload (0.0 / 0001-01-01) must raise SWWApiError."""
    client, _ = make_client(
        LOGIN_OK,
        (200, {"totalUsage": "53.431", "latestReadingDateTime": "2026-06-14T23:00:00Z"}),
        LOGIN_OK,
        (200, {"totalUsage": 0, "latestReadingDateTime": "0001-01-01T00:00:00"}),
    )
    first_usage = await client.async_get_year_to_date(NOW)
    assert first_usage.total_usage_m3 == pytest.approx(53.431)

    with pytest.raises(SWWApiError):
        await client.async_get_year_to_date(NOW)


async def test_usage_drop_without_rollover_fails() -> None:
    client, _ = make_client(
        LOGIN_OK,
        (200, {"totalUsage": "53.431", "latestReadingDateTime": "2026-06-14T23:00:00Z"}),
        LOGIN_OK,
        (200, {"totalUsage": "40.000", "latestReadingDateTime": "2026-06-15T23:00:00Z"}),
    )
    await client.async_get_year_to_date(NOW)
    with pytest.raises(SWWApiError):
        await client.async_get_year_to_date(NOW)


async def test_usage_drop_with_year_rollover_succeeds() -> None:
    dec31 = dt.datetime(2026, 12, 31, 10, 0, tzinfo=dt.UTC)
    jan02 = dt.datetime(2027, 1, 2, 10, 0, tzinfo=dt.UTC)
    client, _ = make_client(
        LOGIN_OK,
        (200, {"totalUsage": "99.123", "latestReadingDateTime": "2026-12-31T23:00:00Z"}),
        LOGIN_OK,
        (200, {"totalUsage": "0.456", "latestReadingDateTime": "2027-01-02T10:00:00Z"}),
    )
    first = await client.async_get_year_to_date(dec31)
    assert first.total_usage_m3 == pytest.approx(99.123)

    second = await client.async_get_year_to_date(jan02)
    assert second.total_usage_m3 == pytest.approx(0.456)
    assert second.latest_reading == dt.datetime(2027, 1, 2, 10, tzinfo=dt.UTC)


async def test_connection_error() -> None:
    client, _ = make_client(aiohttp.ClientConnectionError())
    with pytest.raises(SouthWestWaterConnectionError):
        await client.async_login()


async def test_timeout() -> None:
    client, _ = make_client(TimeoutError())
    with pytest.raises(SouthWestWaterConnectionError):
        await client.async_login()
