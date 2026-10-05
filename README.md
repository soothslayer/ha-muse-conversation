# Muse Conversation for Home Assistant

Talk to Muse through a Home Assistant Voice Preview Edition (Voice PE) and hear
its replies on the device. Home Assistant OS runs the Muse Bridge app, so you
do not need a separate Linux computer.

Home Assistant turns your speech into text, sends it to Muse, and reads the
answer aloud through the PE. **This community integration is experimental.**
Muse runs in the cloud, so an internet connection is required.

## What you need

- **Home Assistant OS on a 64-bit ARM or x86 host** (`aarch64` or `amd64`).
  On Raspberry Pi, use **HA OS 18.3 or newer**: 18.2 has a Bluetooth advertising
  regression that can block pairing. Back up HA before updating the OS.
- **Bluetooth on the HA host**, using a built-in or USB adapter supported by HA.
  An ESPHome Bluetooth proxy cannot be used for Muse pairing.
- **A Muse account, the Muse phone app, and a gadget SDK token** from
  [gadgets.muse.ai](https://gadgets.muse.ai). The SDK token is different from a
  saved gadget's pairing credentials or a Home Assistant access token.
- **A Voice PE running official Home Assistant firmware**, joined to Wi-Fi and
  added to HA through ESPHome.
- **Working Assist speech-to-text and text-to-speech providers**. Home Assistant
  Cloud was used in the live test and requires its subscription. You can instead
  configure local providers such as Whisper and Piper; that combination has not
  been tested end to end with this project.

For **Home Assistant Container/Core**, use the
[separate Linux bridge instructions](bridge/README.md) instead of the HA OS app
steps below.

## Set up Home Assistant OS and Voice PE

Install both parts of this project:

- **Muse Bridge app:** connects your HA host to Muse.
- **Muse Conversation integration:** lets Home Assistant Assist use that connection.

Then select Muse as the assistant on your PE. The steps below cover each part.

### 1. Prepare the Voice PE

If the PE already works with Home Assistant Assist, keep its official firmware
and continue to step 2. If it runs custom firmware, follow the
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

This pairs the **HA host** with Muse. A previous Muse pairing on the PE does not
pair the bridge. For migration from an existing gadget, see the
[app documentation](muse_bridge/DOCS.md#migrate-an-existing-gadget).

### 3. Install the Muse Conversation integration

Choose one installation method:

- **HACS:** choose [**Custom repositories**](https://www.hacs.xyz/docs/faq/custom_repositories/)
  from the HACS menu, add
  `https://github.com/soothslayer/ha-muse-conversation` with type **Integration**,
  and download **Muse Conversation**.
- **Manual:** download this repository and copy the entire
  `custom_components/muse_conversation` folder into your HA configuration
  directory, producing `/config/custom_components/muse_conversation/manifest.json`.

Restart **Home Assistant Core** after installing the integration.

With the bridge app running, open **Settings > Devices & services > Add integration**.
Search for **Muse Conversation**, choose **Muse Bridge app / local bridge**, and
leave the socket path at:

```text
/share/muse-conversation/musegadget.sock
```

The **Direct API token** option is not supported; use the bridge option above.

### 4. Set Muse as the PE's assistant

1. Open **Settings > Voice assistants** and add an assistant named **Muse**.
2. Choose your language and set **Conversation agent** to **Muse**.
3. Select your configured **Speech-to-text** and **Text-to-speech** providers.
   With Home Assistant Cloud, select it for both and choose a supported language
   and voice. With local providers, install and configure them first.
4. Save the assistant. Open your Voice PE's device page under **ESPHome** and
   set its **Assistant** selector to **Muse**.

Other devices can keep their existing assistants. You can also leave **Prefer
handling commands locally** enabled so HA can answer supported home-control
requests itself.

### 5. Test text, then voice

1. Open HA's **Assist** dialog, select the **Muse** assistant, and type:
   **“Say hello in one short sentence.”** Wait for an actual answer from Muse.
   “Sent to Muse” is a delivery acknowledgment, not a successful reply test.
2. Press the PE button once, or say its configured wake word (for example,
   **“Okay Nabu”**), then say **“Muse, say hello in one sentence.”**
3. Confirm the PE speaks the answer. Ask another question to check continued use.

Allow a few seconds for the spoken reply. Once it works, make an HA backup that
includes **Home Assistant configuration and the Muse Bridge app**. Keep the
backup private because it contains pairing credentials.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| MuseGadget never appears | Check the app log, host Bluetooth adapter, and phone proximity to the **HA host**. Bluetooth proxies cannot perform this pairing. On Raspberry Pi with HA OS 18.2, update to 18.3 or newer. |
| iPhone reaches Connect, then the gadget disappears | Use the current Muse Bridge app, restart it to reopen the 10-minute window, and complete the phone's Bluetooth pairing prompt. Check for GATT/advertising errors in its log. |
| Integration cannot connect to the socket | Start the bridge app and use `/share/muse-conversation/musegadget.sock`. For Container/Core, follow the [Linux bridge guide](bridge/README.md). |
| Muse gets the message, but Assist returns no answer | Update the Muse Bridge app from this repository and check its log for connection errors. A reply in the phone app does not guarantee that HA received it. |
| Text works, but the PE is silent | Check the PE's **Assistant** assignment, the pipeline's TTS provider, speaker volume and mute state. Try TTS directly to its media player to isolate playback from Muse. |
| One steady red LED nearest the speaker | The PE is in silent mode. Turn the dial clockwise or raise its media-player volume in HA. If HA already shows a nonzero volume, change it slightly to send a fresh setting. |
| Two steady red LEDs nearest the microphones | The microphones are muted; check the hardware microphone switch. |
| “Busy” or a timeout | Wait for the current request to finish. Check Muse before repeating a timed-out request: it may already have been delivered. |

See the [official PE LED guide](https://support.nabucasa.com/hc/en-us/articles/25764604971421-Status-colors-of-the-LEDs-status-LEDs-on-Home-Assistant-Voice-Preview-Edition)
and [bridge app troubleshooting](muse_bridge/DOCS.md#troubleshooting).
When reporting an issue, include HA OS/Core versions, bridge version, phone OS,
and which test failed. Remove tokens and private conversation text from logs.

## Updates and pairing storage

Update the **app** through HA's app store and the **integration** through HACS
(or replace its files manually, then restart Core). Pairing lives in private app
data and survives ordinary app updates and restarts. Back it up before replacing
or uninstalling the app.

## Notifications

Notifications send a message to Muse without waiting for or speaking a reply.
To send one from an HA automation, use:

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

## Limitations

- **One voice request at a time.** A second request receives a busy error.
  Notifications can still be delivered while a reply is pending.
- **Replies take time.** The bridge waits for three seconds of quiet after Muse
  finishes a message. It stops waiting after 80 seconds; Assist may time out
  sooner. Later messages are not included in the spoken reply.
- **A very fast first reply can be missed** while the bridge connects to a new
  chat. It reports a timeout and does not automatically resend the message.
  Cancelling or timing out does not undo work already sent to Muse.
- **Replies are limited to 8 KiB of text.** Missing, incomplete, or oversized
  replies produce an error instead of being spoken as a successful answer.
- **Muse does not gain control of HA devices through this integration.** Home
  control can still use Assist's local command handling.

Each Assist conversation uses its own Muse side chat; follow-ups in that
conversation reuse it. The bridge accepts replies only when it can match them
to the request. See the [Linux bridge guide](bridge/README.md) for protocol details.

## Tested setup

Spoken replies and follow-up messages were verified with:

| Component | Version or provider |
| --- | --- |
| HA host | Raspberry Pi 4 |
| Home Assistant OS | 18.3 |
| Home Assistant Core | 2026.9.2 |
| Voice PE firmware | 26.9.0 |
| Phone used for pairing | iPhone |
| Speech-to-text and text-to-speech | Home Assistant Cloud |

Automated integration tests use HA 2026.9.4. Other hardware and speech providers
have not been verified end to end with this project.

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
