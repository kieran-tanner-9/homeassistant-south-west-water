"""Tests for the South West Water API client (fake data only)."""

from __future__ import annotations

import datetime as dt

import aiohttp
import pytest
import yarl
from aioresponses import aioresponses

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
)

LOGIN_URL = f"{BASE_URL}{LOGIN_PATH}"
USAGE_URL = f"{BASE_URL}{USAGE_PATH}"
NOW = dt.datetime(2026, 6, 15, 10, 30, tzinfo=dt.UTC)


@pytest.fixture
async def client():
    async with aiohttp.ClientSession() as session:
        yield SouthWestWaterClient(session, "user@example.invalid", "fake-pass", "000000")


async def test_login_success(client) -> None:
    with aioresponses() as m:
        m.post(LOGIN_URL, payload={"opOutcomeCode": 1})
        await client.async_login()


async def test_login_bad_credentials(client) -> None:
    with aioresponses() as m:
        m.post(LOGIN_URL, payload={"opOutcomeCode": 0})
        with pytest.raises(SouthWestWaterAuthError):
            await client.async_login()


async def test_login_http_401(client) -> None:
    with aioresponses() as m:
        m.post(LOGIN_URL, status=401)
        with pytest.raises(SouthWestWaterAuthError):
            await client.async_login()


async def test_login_server_error(client) -> None:
    with aioresponses() as m:
        m.post(LOGIN_URL, status=500)
        with pytest.raises(SouthWestWaterResponseError):
            await client.async_login()


async def test_usage_year_to_date(client) -> None:
    with aioresponses() as m:
        m.post(LOGIN_URL, payload={"opOutcomeCode": 1})
        m.post(
            USAGE_URL,
            payload={"totalUsage": "123.456", "latestReadingDateTime": "2026-06-14T23:00:00Z"},
        )
        usage = await client.async_get_year_to_date(NOW)
    assert usage.total_usage_m3 == pytest.approx(123.456)
    assert usage.latest_reading == dt.datetime(2026, 6, 14, 23, tzinfo=dt.UTC)


async def test_usage_request_payload(client) -> None:
    with aioresponses() as m:
        m.post(LOGIN_URL, payload={"opOutcomeCode": 1})
        m.post(USAGE_URL, payload={"totalUsage": 1})
        await client.async_get_year_to_date(NOW)
        call = m.requests[("POST", yarl.URL(USAGE_URL))][0]
    body = call.kwargs["json"]
    assert body["startDateTime"] == "2026-01-01T00:00:00.000Z"
    assert body["endDateTime"] == "2026-06-15T23:59:59.999Z"
    assert body["interval"] == "month"


async def test_usage_without_latest_reading(client) -> None:
    with aioresponses() as m:
        m.post(LOGIN_URL, payload={"opOutcomeCode": 1})
        m.post(USAGE_URL, payload={"totalUsage": 5})
        usage = await client.async_get_year_to_date(NOW)
    assert usage.latest_reading is None


async def test_usage_missing_total(client) -> None:
    with aioresponses() as m:
        m.post(LOGIN_URL, payload={"opOutcomeCode": 1})
        m.post(USAGE_URL, payload={"other": 1})
        with pytest.raises(SouthWestWaterResponseError):
            await client.async_get_year_to_date(NOW)


async def test_usage_reauthenticates_on_401(client) -> None:
    with aioresponses() as m:
        m.post(LOGIN_URL, payload={"opOutcomeCode": 1})
        m.post(USAGE_URL, status=401)
        m.post(LOGIN_URL, payload={"opOutcomeCode": 1})
        m.post(USAGE_URL, payload={"totalUsage": 9})
        usage = await client.async_get_year_to_date(NOW)
    assert usage.total_usage_m3 == 9


async def test_usage_auth_failure_after_retry(client) -> None:
    with aioresponses() as m:
        m.post(LOGIN_URL, payload={"opOutcomeCode": 1})
        m.post(USAGE_URL, status=401)
        m.post(LOGIN_URL, payload={"opOutcomeCode": 1})
        m.post(USAGE_URL, status=401)
        with pytest.raises(SouthWestWaterAuthError):
            await client.async_get_year_to_date(NOW)


async def test_connection_error(client) -> None:
    with aioresponses() as m:
        m.post(LOGIN_URL, exception=aiohttp.ClientConnectionError())
        with pytest.raises(SouthWestWaterConnectionError):
            await client.async_login()


async def test_timeout(client) -> None:
    with aioresponses() as m:
        m.post(LOGIN_URL, exception=TimeoutError())
        with pytest.raises(SouthWestWaterConnectionError):
            await client.async_login()
