"""Transport layer between Home Assistant and Muse.

Status as of October 2026: Meta has NOT published a public HTTP chat API for
Muse. The open-source gadget SDK (facebookincubator/muse-gadget-sdk) pairs
devices with the Muse app over Bluetooth; its ``mgst_...`` tokens are device
pairing tokens, not chat API keys.

MuseClient isolates the transport behind one interface so the Home Assistant
plumbing (config flow, conversation entity) stays stable while the last mile
is worked out. Candidate paths:

1. A future public Muse HTTP API -- implement it here as HttpMuseClient.
2. A local bridge: run the Linux gadget SDK on the HA host and relay through
   it. Note that ``musegadget send-user-msg`` is one-way (it posts into a
   Muse chat); a request/response path back to the caller is not documented.

Do not invent an endpoint. When Meta documents one, this is the only file
that needs to change.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class MuseAPIError(Exception):
    """Raised when Muse cannot be reached or returns an error."""


class MuseClient(ABC):
    """Sends text to Muse and returns the reply text."""

    def __init__(self, token: str) -> None:
        """Store the token; subclasses decide how to use it."""
        self._token = token

    @abstractmethod
    async def async_send_message(
        self, text: str, conversation_id: str | None
    ) -> str:
        """Send a message to Muse and return the reply text."""


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
