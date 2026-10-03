"""Notify platform for Muse: one-way delivery via the local gadget bridge."""

from __future__ import annotations

from typing import Any

from homeassistant.components.notify import BaseNotificationService
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .muse_client import MuseAPIError, MuseClient


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Muse notify service."""
    client: MuseClient = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MuseNotificationService(client)])


class MuseNotificationService(BaseNotificationService):
    """Send notifications to your Muse via the local gadget bridge."""

    def __init__(self, client: MuseClient) -> None:
        """Initialize the service."""
        self._client = client

    @property
    def name(self) -> str:
        """Return the name of the notify service."""
        return "muse"

    async def async_send_message(self, message: str = "", **kwargs: Any) -> None:
        """Deliver a notification to Muse.

        Keyword args: title (prepended to the message), target or
        data: {session_id: ...} to pick a Muse side chat.
        """
        title = kwargs.get("title")
        text = f"{title}: {message}" if title else message
        data: dict[str, Any] = kwargs.get("data") or {}
        session_id = data.get("session_id")
        if not session_id:
            target = kwargs.get("target")
            if isinstance(target, list) and target:
                session_id = target[0]
            elif isinstance(target, str):
                session_id = target
        try:
            await self._client.async_send_message(text, session_id)
        except MuseAPIError as err:
            raise HomeAssistantError(f"Could not notify Muse: {err}") from err
