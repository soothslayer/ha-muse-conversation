"""Use real Home Assistant response and chat-log types."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from homeassistant.components.conversation.chat_log import ChatLog
from homeassistant.components.notify import NotifyEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from custom_components.muse_conversation.conversation import MuseConversationEntity
from custom_components.muse_conversation.muse_client import MuseAPIError, create_client
from custom_components.muse_conversation.notify import MuseNotificationEntity


async def test_muse_reply_is_speech_and_history_with_stable_side_chat(tmp_path):
    hass = HomeAssistant(str(tmp_path))
    client = SimpleNamespace(
        async_send_message=AsyncMock(return_value="The kitchen lights are on.")
    )
    entity = MuseConversationEntity(SimpleNamespace(entry_id="config-1"), client)
    # Test an HA ID that isn't itself valid as a Muse session ID.
    chat_log = ChatLog(hass, "ha:conversation/123")
    user = SimpleNamespace(
        text="Lights on",
        language="en",
        agent_id="conversation.muse",
        conversation_id=None,
    )
    result = await entity._async_handle_message(user, chat_log)
    assert (
        result.response.as_dict()["speech"]["plain"]["speech"]
        == "The kitchen lights are on."
    )
    assert result.conversation_id == "ha:conversation/123"
    assert chat_log.content[-1].content == "The kitchen lights are on."
    first_session = client.async_send_message.call_args.args[1]
    assert client.async_send_message.call_args.kwargs == {"wait_for_reply": True}
    await entity._async_handle_message(user, chat_log)
    assert client.async_send_message.call_args.args[1] == first_session
    await entity._async_handle_message(user, ChatLog(hass, "different"))
    assert client.async_send_message.call_args.args[1] != first_session


async def test_bridge_failure_is_spoken_and_recorded(tmp_path):
    client = SimpleNamespace(
        async_send_message=AsyncMock(side_effect=MuseAPIError("Bridge offline"))
    )
    entity = MuseConversationEntity(SimpleNamespace(entry_id="config-1"), client)
    chat_log = ChatLog(HomeAssistant(str(tmp_path)), "ha-1")
    user = SimpleNamespace(text="Hello", language="en", agent_id="conversation.muse")
    result = await entity._async_handle_message(user, chat_log)
    assert "Bridge offline" in result.response.as_dict()["speech"]["plain"]["speech"]
    assert "Bridge offline" in chat_log.content[-1].content


async def test_notification_is_a_real_entity_and_does_not_wait():
    client = SimpleNamespace(async_send_message=AsyncMock())
    entity = MuseNotificationEntity(SimpleNamespace(entry_id="config-1"), client)
    assert isinstance(entity, NotifyEntity)
    await entity.async_send_message("Door open", title="Garage")
    client.async_send_message.assert_awaited_once_with("Garage: Door open", None)
    client.async_send_message.side_effect = MuseAPIError("offline")
    with pytest.raises(HomeAssistantError, match="offline"):
        await entity.async_send_message("Hello")


async def test_factory_imports_and_stub_does_not_claim_success():
    from custom_components.muse_conversation.muse_client import LocalBridgeMuseClient

    assert isinstance(
        create_client({"transport": "local_bridge"}), LocalBridgeMuseClient
    )
    with pytest.raises(MuseAPIError, match="No public Muse chat API"):
        await create_client({"transport": "api_token"}).async_send_message(
            "Hi", None, wait_for_reply=True
        )


async def test_legacy_notification_action_keeps_side_chat_support(tmp_path):
    from custom_components.muse_conversation.muse_client import LocalBridgeMuseClient
    from custom_components.muse_conversation.notify import async_setup_entry

    hass = HomeAssistant(str(tmp_path))
    client = LocalBridgeMuseClient()
    client.async_send_message = AsyncMock()
    cleanup = []
    entry = SimpleNamespace(entry_id="entry", async_on_unload=cleanup.append)
    hass.data["muse_conversation"] = {"entry": client}
    entities = []
    await async_setup_entry(hass, entry, entities.extend)
    await hass.services.async_call(
        "notify",
        "muse",
        {
            "message": "Hi",
            "title": "Title",
            "data": {"session_id": "side-1"},
        },
        blocking=True,
    )
    client.async_send_message.assert_awaited_once_with("Title: Hi", "side-1")
    assert isinstance(entities[0], NotifyEntity)
    cleanup[0]()
    assert not hass.services.has_service("notify", "muse")
