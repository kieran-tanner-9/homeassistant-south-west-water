"""Config flow for South West Water."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import SouthWestWaterClient
from .const import (
    CONF_METER_REF,
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
from .exceptions import (
    SouthWestWaterAuthError,
    SouthWestWaterConnectionError,
    SouthWestWaterError,
)

_LOGGER = logging.getLogger(__name__)

PASSWORD_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))
TARIFF_SELECTOR = NumberSelector(NumberSelectorConfig(min=0.0, mode=NumberSelectorMode.BOX))

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): PASSWORD_SELECTOR,
        vol.Required(CONF_METER_REF): str,
    }
)
REAUTH_SCHEMA = vol.Schema({vol.Required(CONF_PASSWORD): PASSWORD_SELECTOR})


def get_tariff_schema(options: Mapping[str, Any] | None = None) -> vol.Schema:
    """Return tariff schema with current or default values."""
    opts = options or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_WATER_RATE,
                default=float(opts.get(CONF_WATER_RATE, DEFAULT_WATER_RATE)),
            ): TARIFF_SELECTOR,
            vol.Required(
                CONF_SEWERAGE_RATE,
                default=float(opts.get(CONF_SEWERAGE_RATE, DEFAULT_SEWERAGE_RATE)),
            ): TARIFF_SELECTOR,
            vol.Required(
                CONF_WATER_STANDING_CHARGE,
                default=float(opts.get(CONF_WATER_STANDING_CHARGE, DEFAULT_WATER_STANDING_CHARGE)),
            ): TARIFF_SELECTOR,
            vol.Required(
                CONF_SEWERAGE_STANDING_CHARGE,
                default=float(
                    opts.get(CONF_SEWERAGE_STANDING_CHARGE, DEFAULT_SEWERAGE_STANDING_CHARGE)
                ),
            ): TARIFF_SELECTOR,
        }
    )


class SouthWestWaterConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for South West Water."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._user_input: dict[str, Any] = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
        return SouthWestWaterOptionsFlow()

    async def _async_check_login(self, username: str, password: str, meter_ref: str) -> str | None:
        """Try to log in, returning an error key on failure."""
        client = SouthWestWaterClient(
            async_create_clientsession(self.hass), username, password, meter_ref
        )
        try:
            await client.async_login()
        except SouthWestWaterAuthError:
            return "invalid_auth"
        except SouthWestWaterConnectionError:
            return "cannot_connect"
        except SouthWestWaterError:
            return "unknown"
        return None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial credentials step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            meter_ref = user_input[CONF_METER_REF].strip()
            self._user_input = {
                **user_input,
                CONF_USERNAME: user_input[CONF_USERNAME].strip(),
                CONF_METER_REF: meter_ref,
            }
            await self.async_set_unique_id(meter_ref)
            self._abort_if_unique_id_configured()
            error = await self._async_check_login(
                self._user_input[CONF_USERNAME], self._user_input[CONF_PASSWORD], meter_ref
            )
            if error is None:
                return await self.async_step_tariffs()
            errors["base"] = error
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                USER_SCHEMA,
                {k: v for k, v in (user_input or {}).items() if k != CONF_PASSWORD},
            ),
            errors=errors,
        )

    async def async_step_tariffs(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle configuring water tariffs and standing charges."""
        if user_input is not None:
            return self.async_create_entry(
                title=NAME,
                data=self._user_input,
                options=user_input,
            )
        return self.async_show_form(
            step_id="tariffs",
            data_schema=get_tariff_schema(),
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        """Start reauthentication when stored credentials stop working."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for a new password."""
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            error = await self._async_check_login(
                entry.data[CONF_USERNAME],
                user_input[CONF_PASSWORD],
                entry.data[CONF_METER_REF],
            )
            if error is None:
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_PASSWORD: user_input[CONF_PASSWORD]}
                )
            errors["base"] = error
        return self.async_show_form(
            step_id="reauth_confirm", data_schema=REAUTH_SCHEMA, errors=errors
        )


class SouthWestWaterOptionsFlow(OptionsFlow):
    """Handle options flow for South West Water."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=get_tariff_schema(self.config_entry.options),
        )
