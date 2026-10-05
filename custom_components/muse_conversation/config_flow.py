"""Config flow for the Muse Conversation integration."""

from __future__ import annotations

import asyncio
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_TOKEN
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    CONF_SOCKET_PATH,
    CONF_TRANSPORT,
    DEFAULT_SOCKET_PATH,
    DOMAIN,
    TRANSPORT_API,
    TRANSPORT_LOCAL_BRIDGE,
)


class MuseConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Muse Conversation."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pick how Home Assistant reaches Muse."""
        if user_input is not None:
            if user_input[CONF_TRANSPORT] == TRANSPORT_LOCAL_BRIDGE:
                return await self.async_step_bridge()
            return await self.async_step_api_token()

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_TRANSPORT, default=TRANSPORT_LOCAL_BRIDGE
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            {
                                "value": TRANSPORT_LOCAL_BRIDGE,
                                "label": "Local gadget bridge (works today)",
                            },
                            {
                                "value": TRANSPORT_API,
                                "label": "Direct API token (not yet available)",
                            },
                        ],
                        mode=SelectSelectorMode.LIST,
                    )
                )
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_bridge(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure the local musegadget bridge."""
        errors: dict[str, str] = {}
        if user_input is not None:
            socket_path = (
                user_input.get(CONF_SOCKET_PATH) or ""
            ).strip() or DEFAULT_SOCKET_PATH
            if not await self._socket_reachable(socket_path):
                errors["base"] = "socket_unreachable"
            else:
                await self.async_set_unique_id(f"{DOMAIN}_{TRANSPORT_LOCAL_BRIDGE}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Muse (local bridge)",
                    data={
                        CONF_TRANSPORT: TRANSPORT_LOCAL_BRIDGE,
                        CONF_SOCKET_PATH: socket_path,
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SOCKET_PATH, default=DEFAULT_SOCKET_PATH
                ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
            }
        )
        return self.async_show_form(step_id="bridge", data_schema=schema, errors=errors)

    async def async_step_api_token(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Store a token for a future public API (stub for now)."""
        errors: dict[str, str] = {}
        if user_input is not None:
            token = (user_input.get(CONF_TOKEN) or "").strip()
            if token:
                await self.async_set_unique_id(f"{DOMAIN}_{TRANSPORT_API}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Muse",
                    data={CONF_TRANSPORT: TRANSPORT_API, CONF_TOKEN: token},
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
            step_id="api_token", data_schema=schema, errors=errors
        )

    async def _socket_reachable(self, socket_path: str) -> bool:
        """Check that the musegadget service socket accepts a connection."""
        try:
            _reader, writer = await asyncio.wait_for(
                asyncio.open_unix_connection(socket_path), timeout=5
            )
        except (OSError, asyncio.TimeoutError):
            return False
        writer.close()
        await writer.wait_closed()
        return True
