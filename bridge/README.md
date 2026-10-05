# Linux bridge support for Assist replies

The upstream Linux SDK's `/chat/stream` response is a delivery acknowledgment.
The ESP32 SDK also opens `/chat/subscribe` on the same encrypted connection and
collects `delta.message_start`, `delta.text_append`, `delta.message_done` and
`message.assistant` events. This patch brings that receive path to Linux.

This is an experimental companion patch, not an upstream release. It is pinned
to SDK commit `3229892e93c18a768ace42cbe1fe7133f91ca203` and includes regression
tests. It does not change pairing cryptography, Noise cryptography, or firmware.
The Bluetooth advertisement explicitly requests discoverability for modern
BlueZ/kernel validation.

## Build and test

On a Linux host, clone this integration and the SDK into sibling directories:

```sh
git clone https://github.com/soothslayer/ha-muse-conversation.git
git clone https://github.com/facebookincubator/muse-gadget-sdk.git
cd muse-gadget-sdk
git checkout 3229892e93c18a768ace42cbe1fe7133f91ca203
git apply --check ../ha-muse-conversation/muse_bridge/musegadget-spoken-replies.patch
git apply ../ha-muse-conversation/muse_bridge/musegadget-spoken-replies.patch
cd linux
uv run --with pytest --with . pytest -q
```

While testing a draft PR, check out that PR's branch in the integration clone
before applying its patch. Do not apply the patch to an arbitrary newer SDK
revision: rebase and rerun its tests first.

Install from the patched directory following the SDK's installer:

```sh
bash install.sh --from .
```

The installer retains an existing pairing. Restarting interrupts any commands
Muse is currently executing on the bridge; check the service log before doing so.
For a new bridge, pair it using `sudo musegadget pair` and the Muse phone app.
The Voice PE's separate firmware pairing does not pair the Linux service.

## Verify before using voice

Run as an account permitted to access the service socket:

```sh
python3 - <<'PY'
import json
import socket
import uuid

with socket.socket(socket.AF_UNIX) as sock:
    sock.settimeout(90)
    sock.connect('/run/musegadget/musegadget.sock')
    sock.sendall((json.dumps({
        'message': 'Say hello in one short sentence.',
        'session_id': str(uuid.uuid4()),
        'wait_for_reply': True,
    }) + '\n').encode())
    print(json.loads(sock.makefile('rb').readline()))
PY
```

Expected: `{"ok": true, ..., "reply": "...Muse's answer..."}`. An `ok` response
with only `response.accepted` means the running bridge is unpatched. Check
`sudo journalctl -u musegadget` for service errors; do not share tokens or private
chat text when reporting a failure.

After this succeeds, test the HA Assist text UI, then speech on the Voice PE.
If the call times out despite an app reply, the service may lack the parent-ID
metadata required for safe reply correlation. Capture a **redacted event shape**
in a development environment to investigate; the patch deliberately does not
log conversation contents or fall back to arbitrary account-wide replies.

## Local protocol

Existing clients are unchanged:

```json
{"message":"Notification", "session_id":"optional-side-chat"}
```

Assist opts into reply waiting:

```json
{"message":"Question", "session_id":"ha-chat-id", "wait_for_reply":true}
```

The success response retains `ok`, `status`, and `response` from the acknowledgment
and adds `reply` as text. Failures return `ok: false` with `error`. Keep the socket
open while waiting; EOF cancels the wait. Subscription failure before posting does
not send the question. A later timeout does not imply the question was unsent.

No public Muse HTTP chat API is invented here: both endpoints run inside the
SDK's existing authenticated Noise connection.
