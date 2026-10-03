"""Config flow for the Muse Conversation integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_TOKEN
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import DOMAIN


class MuseConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Muse Conversation."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            token = user_input[CONF_TOKEN].strip()
            if token:
                await self.async_set_unique_id(DOMAIN)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Muse",
                    data={CONF_TOKEN: token},
                )
            errors["base"] = "empty_token"

        schema = vol.Schema(
            {
                vol.Required(CONF_TOKEN): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.PASSWORD)
                ),
            }
        )
        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )
