# Muse Conversation for Home Assistant

Talk to Muse through a Home Assistant Voice Preview Edition (Voice PE) and hear
its replies on the device. Home Assistant OS runs the Muse Bridge app, so you
need **only your HA host and Voice PE—no separate Linux computer**.

```text
Voice PE microphone -> Home Assistant Assist speech-to-text
  -> Muse Conversation integration -> Muse Bridge app -> Muse
  -> reply text -> Assist text-to-speech -> Voice PE speaker
```

This is an experimental community integration. Muse still runs in the cloud and
requires an internet connection, a Muse account and gadget SDK access. Local
speech-to-text and text-to-speech do not make Muse itself offline.

## What you need

- **Home Assistant OS on a 64-bit ARM or x86 host** (`aarch64` or `amd64`).
  On Raspberry Pi, use **HA OS 18.3 or newer**: 18.2 has a Bluetooth advertising
  regression that can block pairing. Back up HA before updating the OS.
- **A local Bluetooth adapter on the HA host**, available to HA's BlueZ service.
  Pairing happens beside this host. An ESPHome Bluetooth proxy or the PE's own
  Bluetooth connection cannot replace this adapter.
- **The Muse phone app and a gadget SDK token** from
  [gadgets.muse.ai](https://gadgets.muse.ai). The SDK token is different from a
  saved gadget's pairing credentials or a Home Assistant access token.
- **A Voice PE running official Home Assistant firmware**, joined to Wi-Fi and
  added to HA through ESPHome.
- **Working Assist speech-to-text and text-to-speech providers**. Home Assistant
  Cloud was used in the live test and requires its subscription. You can instead
  configure local providers such as Whisper and Piper; that combination has not
  been tested end to end with this project.

The verified setup used a Raspberry Pi 4, HA OS **18.3**, HA Core **2026.9.2**,
Voice PE firmware **26.9.0**, an **iPhone** for pairing, and Home Assistant Cloud
for speech recognition and TTS. New-chat and follow-up replies, including the
complete microphone-to-speaker flow, were confirmed on that setup. Automated
integration tests use HA **2026.9.4**; other hardware and versions may vary.

For **Home Assistant Container/Core**, use the
[separate Linux bridge instructions](bridge/README.md) instead of the HA OS app
steps below. Mount the socket directory into HA Container and give HA permission
to access it. That service uses `/run/musegadget/musegadget.sock`.

## Set up Home Assistant OS and Voice PE

You install two parts from this repository: the **Muse Bridge app** maintains
the paired Muse connection; the **Muse Conversation integration** makes it an
Assist conversation agent. Installing either one alone is insufficient.

### 1. Prepare the Voice PE

If the PE already works with Home Assistant Assist, keep its official firmware
and continue. If it currently runs custom Muse/voice-ai firmware, follow the
[official firmware recovery guide](https://support.nabucasa.com/hc/en-us/articles/25800241218717-Reinstalling-the-firmware-on-Home-Assistant-Voice-Preview-Edition),
then add the device to HA. Reinstalling firmware replaces its existing setup;
keep any backup you need first.

Confirm the PE is available in **Settings > Devices & services > ESPHome**.
Set a comfortable speaker volume and make sure its microphones are unmuted.

### 2. Install and pair the Muse Bridge app

1. Open **Settings > Apps > App store** (called **Add-ons** on older HA versions).
   In the store's menu, choose **Repositories** and add:

   ```text
   https://github.com/soothslayer/ha-muse-conversation
   ```

2. Find **Muse Bridge** in the store and install it. The first installation
   builds the app image and can take several minutes.
3. Open the app's **Configuration** tab, put your Muse gadget SDK token in
   `sdk_token`, and save. Keep **Start on boot** enabled.
4. Start the app and open its **Log** tab. Find the advertised Bluetooth name,
   **MuseGadget…**. Each installation has its own suffix; use the name in your log.
5. With your phone **near the HA host**, open Muse **Settings > Devices >
   Add device**, select that gadget, and finish **Connect**, including the phone's
   Bluetooth pairing prompt. Use the existing network connection when offered:
   the HA host already has networking.
6. Wait for setup to finish in Muse and for the bridge log to show registration
   with Muse. Seeing the gadget in the discovery list alone is not completion.
   The pairing window lasts **10 minutes**; restart the app to reopen it if needed.

The app includes the iPhone pairing handling used in the verified setup. You do
not need to disable Bluetooth security or mark all nearby devices trusted.
Pair the **HA bridge**, even if this PE was previously paired with Muse while
running different firmware. Fresh pairing is the normal setup path; advanced
credential migration is covered in the [app documentation](muse_bridge/DOCS.md).

### 3. Install the Muse Conversation integration

Choose one installation method:

- **HACS:** open HACS, choose [**Custom repositories**](https://www.hacs.xyz/docs/faq/custom_repositories/) from its menu, add
  `https://github.com/soothslayer/ha-muse-conversation` with type **Integration**,
  and download **Muse Conversation**.
- **Manual:** download this repository and copy the entire
  `custom_components/muse_conversation` folder into your HA configuration
  directory, producing `/config/custom_components/muse_conversation/manifest.json`.

Restart **Home Assistant Core** after installing the integration. Adding the
repository to the app store in step 2 does not install the integration in HACS.

Then open **Settings > Devices & services > Add integration**, search for
**Muse Conversation**, and choose **Muse Bridge app / local bridge**. Leave the
socket path at:

```text
/share/muse-conversation/musegadget.sock
```

The bridge must be running for this step. Do not select **Direct API token**:
that option is a nonfunctional placeholder, not an alternative pairing method.

### 4. Create an Assist pipeline and assign it to the PE

1. Open **Settings > Voice assistants** and add an assistant named **Muse**.
2. Choose your language and set **Conversation agent** to **Muse**.
3. Select your configured **Speech-to-text** and **Text-to-speech** providers.
   With Home Assistant Cloud, select it for both and choose a supported language
   and voice. With local providers, install and configure them first.
4. Save the assistant. Open your Voice PE's device page under **ESPHome** and
   set its **Assistant** selector to **Muse**. Merely creating an assistant does
   not change the one used by the PE.

You can leave other devices on their existing assistants. The optional setting
that handles commands locally first can remain enabled; ordinary HA commands
may then be handled locally instead of going to Muse.

### 5. Test text, then voice

1. Open HA's **Assist** dialog, select the **Muse** assistant, and type:
   **“Say hello in one short sentence.”** Wait for an actual answer from Muse.
   “Sent to Muse” is a delivery acknowledgment, not a successful reply test.
2. Press the PE button once, or say its configured wake word (for example,
   **“Okay Nabu”**), then say **“Muse, say hello in one sentence.”**
3. Confirm the PE speaks the answer. Ask another question to check continued use.

There is a short delay after Muse finishes its response while the bridge waits
for additional reply text. Requests that take too long can time out; see the
limits below. Once working, make an HA backup that includes **Home Assistant
configuration and the Muse Bridge app**. Treat it as sensitive: it contains the
bridge's pairing credentials.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| MuseGadget never appears | Check the app log, host Bluetooth adapter, and phone proximity to the **HA host**. Bluetooth proxies cannot perform this pairing. On Raspberry Pi with HA OS 18.2, update to 18.3 or newer. |
| iPhone reaches Connect, then the gadget disappears | Use the current Muse Bridge app, restart it to reopen the 10-minute window, and complete the phone's Bluetooth pairing prompt. Check for GATT/advertising errors in its log. |
| Integration cannot connect to the socket | Start the bridge and verify `/share/muse-conversation/musegadget.sock`. Container/Core installations use a different path and need a directory mount and permissions. |
| Muse gets the message, but Assist returns no answer | Confirm you installed this repository's patched bridge, not the upstream acknowledgment-only SDK. Check the app log for connection errors. A phone reply proves delivery, but does not prove the bridge received it. |
| Text works, but the PE is silent | Check the PE's **Assistant** assignment, the pipeline's TTS provider, speaker volume and mute state. Try TTS directly to its media player to isolate playback from Muse. |
| One steady red LED nearest the speaker | The PE is in silent mode. Turn the dial clockwise or raise its media-player volume in HA. If HA already shows a nonzero volume, change it slightly to send a fresh setting. |
| Two steady red LEDs nearest the microphones | The microphones are muted; check the hardware microphone switch. |
| “Busy” or a timeout | The bridge supports one active voice request. Let it finish before retrying. A timeout does not mean the message was unsent; check Muse before repeating a request with side effects. |

See the [official PE LED guide](https://support.nabucasa.com/hc/en-us/articles/25764604971421-Status-colors-of-the-LEDs-status-LEDs-on-Home-Assistant-Voice-Preview-Edition)
and [bridge app troubleshooting](muse_bridge/DOCS.md#troubleshooting).
When reporting an issue, include HA OS/Core versions, bridge version, phone OS,
and which test failed. Remove tokens and private conversation text from logs.

## Updates and pairing storage

Update the **app** through HA's app store and the **integration** through HACS
(or replace its files manually, then restart Core). Pairing lives in private app
data and survives ordinary app updates and restarts. Back it up before replacing
or uninstalling the app.

If you installed a preview using a repository URL ending in
`#feat/assist-spoken-replies`, keep that source available until you migrate the
installation. Changing a repository URL can create a separate app-store entry;
do not uninstall a working paired bridge just to change its source.
New installations should use the branch-free repository URL above.

## How this relates to voice-ai

The [voice-pe-spoken-replies branch](https://github.com/soothslayer/voice-ai/tree/voice-pe-spoken-replies)
added speech to Muse's ESP32 firmware. This project uses the same reply protocol:
`/chat/stream` and `/chat/subscribe` over the paired, encrypted gadget connection.
The patched Linux SDK runs inside the HA app and returns reply text to Assist;
HA handles TTS and speaker playback. The custom ESP32 firmware and `voice-ai`
HTTP TTS server are not needed for this setup.

The bridge exposes a local Unix socket, not an HTTP port, and advertises no shell
or file commands to Muse. The unmodified upstream Linux SDK only acknowledges
message delivery; updating the HA integration alone cannot add spoken replies.

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
