# Muse Conversation for Home Assistant

Use Muse as the conversation agent in a Home Assistant Assist pipeline. Assist
sends the transcript to Muse, receives its answer, and uses the pipeline's TTS
engine (for example, local Piper) to speak it on a Voice Preview Edition.

**Spoken replies are experimental. Home Assistant OS can host the bridge as an app; no separate Linux computer is needed.**
The code is tested with simulated Muse events and Home Assistant 2026.9.4; live
Muse replies and Voice PE playback still need verification. The unmodified Linux
SDK only acknowledges delivery, so updating this integration alone is insufficient.

## What carries over from voice-ai

The working [voice-pe-spoken-replies branch](https://github.com/soothslayer/voice-ai/tree/voice-pe-spoken-replies)
adds Piper playback to Muse's ESP32 firmware. Its reply text comes from Muse's
`/chat/subscribe` stream over the paired, encrypted gadget connection.

This integration uses that same reply protocol in the Linux bridge. The flow is:

```text
Voice PE with Home Assistant firmware
  -> Assist speech-to-text
  -> Muse Conversation
  -> patched musegadget Unix socket
  -> Muse /chat/stream + /chat/subscribe over the paired Noise session
  -> answer text -> Assist TTS (Piper) -> Voice PE speaker
```

Home Assistant supplies TTS and playback, so the custom ESP32 speech patch and
`voice-ai` HTTP TTS server are not needed for this route. A Voice PE still running
Muse firmware is not an Assist satellite: restore its Home Assistant firmware and
connect it to HA before using this pipeline. See the
[official Voice PE recovery guide](https://support.nabucasa.com/hc/en-us/articles/25800241218717-Reinstalling-the-firmware).

## Home Assistant OS: Muse Bridge app

Install and pair the [Muse Bridge app](muse_bridge/DOCS.md) on the same Home
Assistant box. It runs the patched SDK, stores pairing credentials in private
app data, and shares `/share/muse-conversation/musegadget.sock` with HA Core.
It exposes no network port and advertises no shell or file commands to Muse.
On Raspberry Pi, use HA OS 18.3 or newer to avoid its Bluetooth advertising
regression. Bluetooth on the HA host is needed for initial phone pairing; the PE's own
pairing does not pair this app. Bluetooth proxy devices cannot supply this
local BlueZ pairing service.

The app currently needs a Muse gadget SDK token from [gadgets.muse.ai](https://gadgets.muse.ai).
Live pairing and replies on HA OS are still being validated.

For Home Assistant Container/Core, [bridge/README.md](bridge/README.md) covers
installing the patched Linux service on the HA host. Its socket remains
`/run/musegadget/musegadget.sock`; enter that path explicitly. Mount the socket
**directory** into HA Container and allow HA to access its group permissions.

## Install and configure

1. Copy `custom_components/muse_conversation` into your HA `custom_components`
   directory (or install this repository as a HACS custom integration) and restart HA.
2. Under **Settings > Devices & services**, add **Muse Conversation**, select
   **Muse Bridge app / local bridge**, and enter the accessible socket path. Existing local
   bridge entries keep their configuration; restart HA after updating the files.
3. Under **Settings > Voice assistants**, create or edit an Assist pipeline:
   select your speech-to-text engine, **Muse** as the conversation agent, and
   **Piper** (or another installed TTS engine) as text-to-speech.
4. Assign that pipeline to the Voice PE running Home Assistant firmware.
5. First test Muse through the Assist text UI, then ask through the Voice PE.
   A successful test returns Muse's actual answer, not “Sent to Muse.”

The **Direct API token** option remains a nonfunctional placeholder, preserved
for existing entries. Device pairing tokens are not public chat API keys.

## Notifications

Notifications remain acknowledgment-only and do not wait for a reply or speak it.
The documented `notify.muse` action is retained for the local bridge:

```yaml
action: notify.muse
data:
  message: "The garage door has been open for an hour."
```

Use `data.session_id` or `target` to choose a Muse side chat (letters, digits and
dashes, at most 64 characters):

```yaml
action: notify.muse
data:
  message: "Summary of today's energy usage?"
  data:
    session_id: "daily-brief"
```

The integration also supplies a native notification entity, normally `notify.muse`,
for main-chat delivery using `notify.send_message`:

```yaml
action: notify.send_message
target:
  entity_id: notify.muse
data:
  title: Garage
  message: "The door is open."
```

## Behavior and limits

- Each HA chat maps to a stable Muse side-chat ID. Follow-up messages in that HA
  chat reuse it; unrelated HA chats get separate IDs.
- The bridge subscribes to the same side chat before posting. For a new chat,
  Muse returns 404 until its first message creates it; the bridge posts once
  and immediately subscribes again. It does not resend the message on failure.
- Replies must link to the acknowledged message, or follow its user-message
  event in the exact side chat with this gadget's source context. Another user
  message interrupts the wait. New chats use the successful creation
  acknowledgment to establish the first turn. Unrelated and unscoped events
  are ignored. Live text replies through HA Assist have been verified.
- A reply completed before a new-chat subscription opens may be missed;
  a timeout is reported instead of resending or speaking an unrelated answer.
- Muse has no explicit end-of-turn event in the SDK protocol. After all accepted
  messages finish, the bridge waits for three seconds of quiet. A later message
  after this window is not included. The total bridge deadline is 80 seconds;
  HA's socket deadline is 90 seconds. Long-running tasks can exceed either the
  bridge deadline or the Assist pipeline's own deadline.
- Only one voice request is active per bridge. A concurrent request gets a spoken
  busy error. Notifications can still be delivered while a voice reply is pending.
- Closing the HA socket cancels the local reply wait and subscription; it does
  not undo the message already delivered to Muse or stop remote work.
- Answers are bounded to 8 KiB of UTF-8 text. Oversized, incomplete, missing or
  malformed responses become spoken errors. The old acknowledgment-only bridge
  produces an instruction to install the patch rather than a false answer.
- This adds Muse conversation replies, not native HA entity/tool control. It does
  not advertise the conversation `CONTROL` feature.

## Development

Python 3.14, tested against Home Assistant 2026.9.4:

```sh
python3.14 -m venv .venv
.venv/bin/pip install -r requirements-test.txt
.venv/bin/pytest -q
.venv/bin/ruff check .
```

The tests use real HA response/chat-log classes and local Unix sockets, without
Muse credentials. The bridge patch includes additional tests plus a real Noise
handshake against a simulated VM; see [bridge/README.md](bridge/README.md).
