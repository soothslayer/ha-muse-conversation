"""Return Muse's answer as Assist speech; the pipeline handles TTS and playback."""

from __future__ import annotations

from typing import Literal
from uuid import NAMESPACE_URL, uuid5

from homeassistant.components import conversation
from homeassistant.components.conversation import ConversationInput, ConversationResult
from homeassistant.components.conversation.chat_log import AssistantContent, ChatLog
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import intent
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .muse_client import MuseAPIError, MuseClient


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Muse conversation entity."""
    client: MuseClient = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MuseConversationEntity(entry, client)])


class MuseConversationEntity(conversation.ConversationEntity):
    """Conversation entity that delivers messages to Muse."""

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
        """Wait for a correlated Muse reply and hand it to Assist's TTS stage."""
        # HA IDs need not satisfy Muse's side-chat rules. A stable mapping keeps
        # follow-ups together without silently routing invalid IDs to main chat.
        session_id = str(
            uuid5(
                NAMESPACE_URL, f"muse:{self._entry.entry_id}:{chat_log.conversation_id}"
            )
        )
        try:
            reply = await self._client.async_send_message(
                user_input.text, session_id, wait_for_reply=True
            )
        except MuseAPIError as err:
            reply = f"Sorry, I couldn't get Muse's reply: {err}"

        chat_log.async_add_assistant_content_without_tools(
            AssistantContent(agent_id=user_input.agent_id, content=reply)
        )
        response = intent.IntentResponse(language=user_input.language)
        response.async_set_speech(reply)
        return ConversationResult(
            response=response,
            conversation_id=chat_log.conversation_id,
        )
