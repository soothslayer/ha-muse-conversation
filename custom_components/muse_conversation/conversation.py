"""Conversation platform for Muse."""

from __future__ import annotations

from typing import Literal

from homeassistant.components import conversation
from homeassistant.components.conversation import ConversationInput, ConversationResult
from homeassistant.components.conversation.chat_log import ChatLog
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import intent
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .muse_client import MuseAPIError, MuseClient, StubMuseClient


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Muse conversation entity."""
    client: MuseClient = StubMuseClient(token=entry.data[CONF_TOKEN])
    async_add_entities([MuseConversationEntity(entry, client)])


class MuseConversationEntity(conversation.ConversationEntity):
    """Conversation entity that answers through Muse."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, entry: ConfigEntry, client: MuseClient) -> None:
        """Initialize the entity."""
        self._entry = entry
        self._client = client
        self._attr_unique_id = entry.entry_id
        self._attr_device_info = dr.DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Muse",
            manufacturer="Meta",
            entry_type=dr.DeviceEntryType.SERVICE,
        )

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        """Return the supported languages."""
        return "*"

    async def _async_handle_message(
        self, user_input: ConversationInput, chat_log: ChatLog
    ) -> ConversationResult:
        """Handle a message from the user and return Muse's reply."""
        try:
            reply = await self._client.async_send_message(
                user_input.text, user_input.conversation_id
            )
        except MuseAPIError as err:
            reply = f"Sorry, I couldn't reach Muse: {err}"

        response = intent.IntentResponse(language=user_input.language)
        response.async_set_speech(reply)
        return ConversationResult(
            response=response,
            conversation_id=user_input.conversation_id,
        )
