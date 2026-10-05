"""Exercise the real Unix socket contract without contacting Muse."""

import asyncio
import json
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

import pytest

from custom_components.muse_conversation.muse_client import (
    LocalBridgeMuseClient,
    MuseAPIError,
)


@asynccontextmanager
async def bridge(response):
    requests = []

    async def handle(reader, writer):
        try:
            requests.append(json.loads(await reader.readline()))
            writer.write(response)
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    # macOS has a short AF_UNIX path limit.
    with tempfile.TemporaryDirectory(dir="/tmp") as directory:
        path = str(Path(directory) / "muse.sock")
        server = await asyncio.start_unix_server(handle, path)
        async with server:
            yield LocalBridgeMuseClient(path), requests


async def test_reply_text_and_notification_use_different_contracts():
    async with bridge(b'{"ok":true,"reply":" The lights are on. "}\n') as (
        client,
        sent,
    ):
        assert (
            await client.async_send_message(
                " Turn on the lights ", "ha-123", wait_for_reply=True
            )
            == "The lights are on."
        )
        assert sent == [
            {
                "message": "Turn on the lights",
                "session_id": "ha-123",
                "wait_for_reply": True,
            }
        ]
    async with bridge(b'{"ok":true}\n') as (client, sent):
        assert await client.async_send_message("Notice", None) == "Sent to Muse."
        assert sent == [{"message": "Notice"}]


@pytest.mark.parametrize(
    "raw, match",
    [
        (b'{"ok":true,"response":{"accepted":true}}\n', "bridge patch"),
        (b'{"ok":true,"reply":" "}\n', "no answer"),
        (b'{"ok":false,"error":"Muse disconnected"}\n', "disconnected"),
        (b'{"ok":true,"reply":42}\n', "no answer"),
        (b"[]\n", "invalid response"),
        (b"broken\n", "Unparseable"),
        (b"\xff\n", "Unparseable"),
        (b"", "closed the connection"),
        (b"x" * 70000 + b"\n", "Lost connection"),
    ],
)
async def test_failures_are_actionable(raw, match):
    async with bridge(raw) as (client, _):
        with pytest.raises(MuseAPIError, match=match):
            await client.async_send_message("Hi", None, wait_for_reply=True)


@pytest.mark.parametrize(
    "text, sid", [(" ", None), ("Hi", "../invalid"), ("x" * 65536, None)]
)
async def test_invalid_input_is_rejected_before_connecting(text, sid):
    with pytest.raises(MuseAPIError):
        await LocalBridgeMuseClient("/missing/socket").async_send_message(text, sid)


async def test_unreachable_bridge():
    with pytest.raises(MuseAPIError, match="Could not reach"):
        await LocalBridgeMuseClient("/missing/socket").async_send_message("Hi", None)


async def test_timeout_and_cancellation_close_the_socket(monkeypatch):
    from custom_components.muse_conversation import muse_client

    monkeypatch.setattr(muse_client, "SOCKET_TIMEOUT_S", 0.03)
    closed = asyncio.Event()

    async def stalled(reader, writer):
        await reader.readline()
        await reader.read()
        closed.set()
        writer.close()

    with tempfile.TemporaryDirectory(dir="/tmp") as directory:
        path = str(Path(directory) / "m.sock")
        async with await asyncio.start_unix_server(stalled, path):
            client = LocalBridgeMuseClient(path)
            with pytest.raises(MuseAPIError, match="Timed out"):
                await client.async_send_message("Hi", None, wait_for_reply=True)
            await asyncio.wait_for(closed.wait(), 1)
            closed.clear()
            task = asyncio.create_task(
                client.async_send_message("Hi", None, wait_for_reply=True)
            )
            await asyncio.sleep(0.01)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            await asyncio.wait_for(closed.wait(), 1)
