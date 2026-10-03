"""Transport layer between Home Assistant and Muse.

Status as of October 2026: Meta has NOT published a public HTTP chat API for
Muse. The open-source gadget SDK (facebookincubator/muse-gadget-sdk) pairs
devices with the Muse app over Bluetooth; its mgst_... tokens are device
pairing tokens, not chat API keys.

MuseClient isolates the transport behind one interface so the Home Assistant
plumbing (config flow, conversation entity, notify service) stays stable
while the last mile is worked out. Two transports ship:

- LocalBridgeMuseClient (works today): talks to the Linux gadget SDK's
  musegadget service over its local Unix socket. The service holds the
  paired, encrypted session to your Muse; we hand it {"message": ...}
  and it POSTs into your Muse chat. This is ONE-WAY: the SDK's
  /chat/stream returns a delivery ack ({"accepted": true}), not
  the reply. Muse's answer lands in the Muse app, not back in Home
  Assistant.
- StubMuseClient: placeholder for a future public HTTP API. Fails loudly
  instead of pretending to call an endpoint that doesn't exist.

Do not invent an endpoint. When Meta documents one, add HttpMuseClient here;
nothing else needs to change.
"""

from __future__ import annotations

import asyncio
import json
import re
from abc import ABC, abstractmethod
from typing import Any

from .const import CONF_SOCKET_PATH, CONF_TOKEN, DEFAULT_SOCKET_PATH, TRANSPORT_LOCAL_BRIDGE


class MuseAPIError(Exception):
    """Raised when Muse cannot be reached or returns an error."""


class MuseClient(ABC):
    """Sends text to Muse and returns what to tell the user."""

    def __init__(self, token: str | None = None) -> None:
        """Store the token; subclasses decide how to use it."""
        self._token = token

    @abstractmethod
    async def async_send_message(
        self, text: str, conversation_id: str | None
    ) -> str:
        """Send a message to Muse and return what to tell the user."""


# Matches the gadget SDK's session-id rule (service.py: _SESSION_ID_RE).
_SESSION_ID_RE = re.compile(r"[A-Za-z0-9-]{1,64}")

# The service waits up to 60s for the VM; the CLI gives the socket 90s.
SOCKET_TIMEOUT_S = 90

# service.py: MAX_LOCAL_REQUEST = 64 * 1024.
MAX_MESSAGE_BYTES = 64 * 1024


class LocalBridgeMuseClient(MuseClient):
    """Deliver messages to Muse through the local musegadget service.

    The service must be installed, paired (musegadget pair), and running
    on the same host as Home Assistant. Messages are posted into your Muse
    chat; replies appear in the Muse app, not here (one-way).
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
        self, text: str, conversation_id: str | None
    ) -> str:
        """Hand the message to the musegadget service and confirm delivery."""
        message = text.strip()
        if not message:
            raise MuseAPIError("Nothing to send: the message was empty.")
        payload: dict[str, Any] = {"message": message}
        session_id = self._session_id(conversation_id)
        if session_id:
            payload["session_id"] = session_id
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
            writer.write(line)
            await writer.drain()
            raw = await asyncio.wait_for(reader.readline(), timeout=SOCKET_TIMEOUT_S)
        except asyncio.TimeoutError as err:
            raise MuseAPIError(
                "Timed out waiting for the musegadget service to deliver the message."
            ) from err
        except OSError as err:
            raise MuseAPIError(
                f"Lost connection to the musegadget service: {err}"
            ) from err
        finally:
            writer.close()
        if not raw:
            raise MuseAPIError(
                "The musegadget service closed the connection without a reply."
            )
        try:
            reply: dict[str, Any] = json.loads(raw)
        except json.JSONDecodeError as err:
            raise MuseAPIError(
                f"Unparseable reply from the musegadget service: {err}"
            ) from err
        if not reply.get("ok"):
            raise MuseAPIError(
                f"Muse did not accept the message: {reply.get('error') or reply}"
            )
        return "Sent to Muse."


class StubMuseClient(MuseClient):
    """Placeholder client until a public Muse chat API exists."""

    async def async_send_message(
        self, text: str, conversation_id: str | None
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
