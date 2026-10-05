"""Local Muse bridge transport; conversations wait for text, notifications for delivery."""

from __future__ import annotations

import asyncio
import json
import re
from abc import ABC, abstractmethod
from typing import Any

from homeassistant.const import CONF_TOKEN

from .const import CONF_SOCKET_PATH, DEFAULT_SOCKET_PATH, TRANSPORT_LOCAL_BRIDGE


class MuseAPIError(Exception):
    """Raised when Muse cannot be reached or returns an error."""


class MuseClient(ABC):
    """Sends text to Muse and returns what to tell the user."""

    def __init__(self, token: str | None = None) -> None:
        """Store the token; subclasses decide how to use it."""
        self._token = token

    @abstractmethod
    async def async_send_message(
        self, text: str, conversation_id: str | None, *, wait_for_reply: bool = False
    ) -> str:
        """Send a message to Muse and return what to tell the user."""


# Matches the gadget SDK's session-id rule (service.py: _SESSION_ID_RE).
_SESSION_ID_RE = re.compile(r"[A-Za-z0-9-]{1,64}")

# Reply-enabled bridges have an 80s overall deadline; leave time for cleanup.
SOCKET_TIMEOUT_S = 90

# service.py: MAX_LOCAL_REQUEST = 64 * 1024.
MAX_MESSAGE_BYTES = 64 * 1024


class LocalBridgeMuseClient(MuseClient):
    """Deliver messages to Muse through the local musegadget service.

    The service must be installed, paired (musegadget pair), and running
    on the same host as Home Assistant. Messages are posted into your Muse
    chat. The companion SDK patch returns reply text when requested.
    """

    def __init__(self, socket_path: str = DEFAULT_SOCKET_PATH) -> None:
        super().__init__(token=None)
        self._socket_path = socket_path

    def _session_id(self, conversation_id: str | None) -> str | None:
        """Map a HA conversation id onto a Muse side-chat id, if valid."""
        if conversation_id and _SESSION_ID_RE.fullmatch(conversation_id):
            return conversation_id
        return None

    async def async_send_message(
        self, text: str, conversation_id: str | None, *, wait_for_reply: bool = False
    ) -> str:
        """Send a message and optionally wait for Muse's answer."""
        message = text.strip()
        if not message:
            raise MuseAPIError("Nothing to send: the message was empty.")
        payload: dict[str, Any] = {"message": message}
        session_id = self._session_id(conversation_id)
        if conversation_id and session_id is None:
            raise MuseAPIError(
                "Invalid Muse conversation ID: use letters, digits and dashes (up to 64)."
            )
        if session_id:
            payload["session_id"] = session_id
        if wait_for_reply:
            payload["wait_for_reply"] = True
        line = (json.dumps(payload) + "\n").encode()
        if len(line) > MAX_MESSAGE_BYTES:
            raise MuseAPIError(
                f"Message is too long ({len(line)} bytes; the service accepts "
                f"{MAX_MESSAGE_BYTES})."
            )
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_unix_connection(self._socket_path),
                timeout=10,
            )
        except (OSError, asyncio.TimeoutError) as err:
            raise MuseAPIError(
                f"Could not reach the musegadget service at {self._socket_path}: "
                f"{err}. Is the service installed, paired, and running on this host?"
            ) from err
        try:
            async with asyncio.timeout(SOCKET_TIMEOUT_S):
                writer.write(line)
                await writer.drain()
                raw = await reader.readline()
        except asyncio.TimeoutError as err:
            raise MuseAPIError(
                "Timed out waiting for Muse. The message may have been delivered."
            ) from err
        except (OSError, ValueError) as err:
            raise MuseAPIError(
                f"Lost connection to the musegadget service: {err}"
            ) from err
        finally:
            writer.close()
            try:
                await asyncio.wait_for(writer.wait_closed(), timeout=1)
            except (OSError, asyncio.TimeoutError):
                pass
        if not raw:
            raise MuseAPIError(
                "The musegadget service closed the connection without a reply."
            )
        try:
            reply: dict[str, Any] = json.loads(raw)
        except (ValueError, UnicodeError) as err:
            raise MuseAPIError(
                f"Unparseable reply from the musegadget service: {err}"
            ) from err
        if not isinstance(reply, dict):
            raise MuseAPIError("The musegadget service returned an invalid response.")
        if reply.get("ok") is not True:
            raise MuseAPIError(
                f"Muse request failed: {reply.get('error') or 'bridge rejected the request'}"
            )
        if wait_for_reply:
            text_reply = reply.get("reply")
            if not isinstance(text_reply, str) or not text_reply.strip():
                raise MuseAPIError(
                    "The bridge delivered the message but returned no answer. "
                    "Install the Muse spoken-replies bridge patch to enable Assist replies."
                )
            return text_reply.strip()
        return "Sent to Muse."


class StubMuseClient(MuseClient):
    """Placeholder client until a public Muse chat API exists."""

    async def async_send_message(
        self, text: str, conversation_id: str | None, *, wait_for_reply: bool = False
    ) -> str:
        """Always fail loudly so nobody mistakes the stub for a live API."""
        raise MuseAPIError(
            "No public Muse chat API is available yet, so this message was "
            "not sent. Implement HttpMuseClient in muse_client.py once Meta "
            "documents an endpoint."
        )


def create_client(data: dict[str, Any]) -> MuseClient:
    """Build the configured transport from a config entry's data."""
    if data.get("transport") == TRANSPORT_LOCAL_BRIDGE:
        return LocalBridgeMuseClient(
            socket_path=data.get(CONF_SOCKET_PATH) or DEFAULT_SOCKET_PATH
        )
    return StubMuseClient(token=data.get(CONF_TOKEN))
