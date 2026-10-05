"""Notification entity for acknowledgment-only delivery to Muse."""

from __future__ import annotations

import voluptuous as vol
from homeassistant.components.notify import NotifyEntity, NotifyEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .muse_client import LocalBridgeMuseClient, MuseAPIError, MuseClient


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Muse notification entity."""
    client: MuseClient = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MuseNotificationEntity(entry, client)])
    # Preserve the documented legacy action while offering a proper entity.
    # Only the single local-bridge entry owns this alias, never the API stub.
    if isinstance(client, LocalBridgeMuseClient) and not hass.services.has_service(
        "notify", "muse"
    ):

        async def send_legacy(call: ServiceCall) -> None:
            data = call.data
            target = data.get("target")
            session_id = data.get("data", {}).get("session_id")
            if not session_id:
                session_id = (
                    target[0] if isinstance(target, list) and target else target
                )
            title = data.get("title")
            text = f"{title}: {data['message']}" if title else data["message"]
            try:
                await client.async_send_message(text, session_id or None)
            except MuseAPIError as err:
                raise HomeAssistantError(f"Could not notify Muse: {err}") from err

        hass.services.async_register(
            "notify",
            "muse",
            send_legacy,
            schema=vol.Schema(
                {
                    vol.Required("message"): cv.string,
                    vol.Optional("title"): cv.string,
                    vol.Optional("target"): vol.Any(cv.string, [cv.string]),
                    vol.Optional("data", default={}): vol.Schema(
                        {vol.Optional("session_id"): cv.string}
                    ),
                }
            ),
        )
        entry.async_on_unload(lambda: hass.services.async_remove("notify", "muse"))


class MuseNotificationEntity(NotifyEntity):
    """Deliver notifications without waiting for an assistant reply."""

    _attr_name = "Muse"
    _attr_supported_features = NotifyEntityFeature.TITLE

    def __init__(self, entry: ConfigEntry, client: MuseClient) -> None:
        self._client = client
        self._attr_unique_id = entry.entry_id

    async def async_send_message(self, message: str, title: str | None = None) -> None:
        """Deliver a notification to the main Muse chat."""
        text = f"{title}: {message}" if title else message
        try:
            await self._client.async_send_message(text, None)
        except MuseAPIError as err:
            raise HomeAssistantError(f"Could not notify Muse: {err}") from err
