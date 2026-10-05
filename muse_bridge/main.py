"""Run the paired Muse connection inside Home Assistant OS."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import subprocess
from pathlib import Path
from types import SimpleNamespace

from musegadget import config, identity
from musegadget.service import Service

_LOGGER = logging.getLogger(__name__)
SHARED_DIR = Path("/share/muse-conversation")


class ConversationOnlyExecutor:
    """No shell or file tools are exposed to Muse from this HA app."""

    account = SimpleNamespace(gid=os.getgid())

    def run(self, command, params, timeout_ms=None):
        return {"ok": False, "error": "This bridge supports conversation only."}


async def run_bridge() -> None:
    service = Service(
        identity=identity.load_or_create(),
        executor=ConversationOnlyExecutor(),
        sdk_token=config.sdk_token(),
        display_name="Home Assistant Muse",
        command_specs={},
    )
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(signum, service.stop)
    server = await service.serve_local(config.socket_path())
    try:
        await service.run()
    finally:
        server.close()
        await server.wait_closed()
        config.socket_path().unlink(missing_ok=True)


def prepare_settings(options_path=Path("/data/options.json")) -> None:
    """Keep credentials in private app data; publish only the local socket."""
    options = json.loads(options_path.read_text())
    token = options.get("sdk_token", "").strip()
    # Optional file import avoids putting a token in terminal history.
    import_path = SHARED_DIR / "sdk_token"
    if not token and import_path.exists():
        token = import_path.read_text().strip()
    if token:
        # Validate without displaying the token on failure.
        os.environ[config.SDK_TOKEN_ENV] = token
        try:
            config.sdk_token()
        finally:
            os.environ.pop(config.SDK_TOKEN_ENV, None)
        state = config.state_dir()
        state.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(state / config.SDK_TOKEN_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as file:
            file.write(token + "\n")
        os.environ.pop(config.SDK_TOKEN_ENV, None)
        if import_path.exists():
            import_path.unlink()
    if not config.sdk_token():
        raise ValueError("Set the app's gadget SDK token before starting.")
    SHARED_DIR.mkdir(mode=0o755, parents=True, exist_ok=True)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    os.environ.setdefault(config.STATE_DIR_ENV, "/data/musegadget")
    os.environ.setdefault(config.SOCKET_ENV, str(SHARED_DIR / "musegadget.sock"))
    prepare_settings()
    if not config.load_json(config.PAIRING_FILE):
        _LOGGER.info("Pair this Home Assistant host in the Muse phone app; see the pairing name below.")
        # This SDK command uses the HA host's BlueZ service through D-Bus.
        child = subprocess.Popen(["/opt/venv/bin/musegadget", "pair", "--timeout", "600"])
        previous = {}
        def stop_pairing(signum, _frame):
            child.send_signal(signum)
        for signum in (signal.SIGTERM, signal.SIGINT):
            previous[signum] = signal.signal(signum, stop_pairing)
        try:
            returncode = child.wait()
        finally:
            for signum, handler in previous.items():
                signal.signal(signum, handler)
        if returncode:
            raise SystemExit("Pairing did not finish. Restart the app to reopen its pairing window.")
    asyncio.run(run_bridge())


if __name__ == "__main__":
    main()
