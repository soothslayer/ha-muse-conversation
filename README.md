# Muse Conversation for Home Assistant

A custom Home Assistant integration that connects **Muse** (Meta's AI agent)
to Home Assistant: send Muse messages from automations, and pick Muse as a
conversation agent.

## How it works (and its limits)

Meta has not published a public HTTP chat API for Muse, so this integration
uses the **local gadget bridge**: Meta's open-source Linux gadget SDK
([muse-gadget-sdk](https://github.com/facebookincubator/muse-gadget-sdk))
running as a service on the same host as Home Assistant. The service holds
your paired, encrypted session to Muse; this integration hands it messages
over a local Unix socket and it posts them into your Muse chat.

**This is one-way.** The SDK's chat endpoint returns a delivery ack, not the
reply. Muse's answer appears in the Muse app, not back in Home Assistant.
So:

- `notify.muse` from automations/scripts: **works today**. "The garage
  door's been open an hour" lands in your Muse chat.
- Conversation entity / voice assistant: accepts what you say, delivers it
  to Muse, and replies "Sent to Muse." The actual answer comes back in the
  app. True two-way voice (ask through a satellite, hear the answer back)
  needs Meta to open a reply channel.

The transport is isolated in `muse_client.py`. If Meta ever documents a real
chat API, that's the one file that changes.

## Prerequisites (bridge)

On the Linux host that runs Home Assistant (needs Bluetooth for pairing):

1. Install the gadget SDK service:
   ```sh
   git clone https://github.com/facebookincubator/muse-gadget-sdk
   cd muse-gadget-sdk/linux
   bash install.sh
   ```
2. Pair it once: `sudo musegadget pair`, then add the device in the Muse
   app (Settings > Devices, Developer mode on).
3. Verify delivery:
   ```sh
   echo "hello from Home Assistant" | musegadget send-user-msg
   # -> "Sent to your Muse." (check the app)
   ```

The service socket defaults to `/run/musegadget/musegadget.sock`. It must be
reachable from Home Assistant, so the service has to run on the same machine.

## Install

### Via HACS (once published)

Add this repo as a custom repository in HACS, install "Muse Conversation",
restart Home Assistant.

### Manual

Copy `custom_components/muse_conversation` into your Home Assistant
`custom_components` directory and restart.

Then **Settings > Devices & Services > Add Integration**, search for
"Muse Conversation", and choose:

- **Local gadget bridge (works today)** — enter the service socket path
  (the default is usually right). The flow checks the socket is reachable.
- **Direct API token (not yet available)** — stores a token for a future
  public Muse API. Currently a stub.

## Usage

**Notify service** (`notify.muse`) in automations and scripts:

```yaml
action: notify.muse
data:
  message: "The garage door has been open for an hour."
```

Target a side chat with `data.session_id` (letters, digits, dashes, up to 64
chars) or `target`:

```yaml
action: notify.muse
data:
  message: "Summary of today's energy usage?"
  data:
    session_id: "daily-brief"
```

**Conversation agent:** pick **Muse** under **Settings > Voice assistants**.
Spoken input is delivered to your Muse chat; you'll hear "Sent to Muse."
back, and the reply appears in the app.

## Layout

```
custom_components/muse_conversation/
├── __init__.py        # config entry setup / unload
├── manifest.json      # integration metadata
├── config_flow.py     # transport choice + socket/token setup
├── conversation.py    # ConversationEntity (one-way delivery)
├── notify.py          # notify.muse service
├── muse_client.py     # transports: LocalBridgeMuseClient, StubMuseClient
├── const.py
├── strings.json
└── translations/en.json
```

## Notes

- Your Home Assistant fork at `~/git/home-assistant-core` is stale (it sits
  at 0.116, from 2020). This integration targets the modern conversation
  entity API, so develop against a current checkout or just drop it into
  your running HA.
- Failures surface as spoken replies / service errors instead of silence.
- `iot_class` is `cloud_polling`; the bridge itself holds a persistent
  session via the musegadget service.
