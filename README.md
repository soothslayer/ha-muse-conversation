# Muse Conversation for Home Assistant

A custom Home Assistant integration that adds **Muse** (Meta's AI agent) as a
conversation agent, so it can answer through your voice assistants and the
Assist pipeline.

## Status: scaffold

The Home Assistant plumbing is complete and follows the current
`ConversationEntity` API (verified against upstream `dev`):

- Config flow with token setup (`config_flow.py`)
- Conversation entity registered as an assistant (`conversation.py`)
- HACS metadata (`hacs.json`)

**The last mile is the transport.** As of October 2026 Meta has not published
a public HTTP chat API for Muse. The gadget SDK
(`facebookincubator/muse-gadget-sdk`) pairs devices with the Muse app over
Bluetooth; its `mgst_...` tokens are device pairing tokens, not chat API
keys. So `muse_client.py` currently ships a stub that fails loudly instead of
pretending to call an endpoint that doesn't exist.

To finish it, implement `HttpMuseClient` in
`custom_components/muse_conversation/muse_client.py` once Meta documents an
endpoint (or build a local bridge around the Linux gadget SDK). Nothing else
needs to change.

## Install

### Via HACS (once published)

Add this repo as a custom repository in HACS, install "Muse Conversation",
restart Home Assistant.

### Manual

Copy `custom_components/muse_conversation` into your Home Assistant
`custom_components` directory and restart.

Then go to **Settings > Devices & Services > Add Integration**, search for
"Muse Conversation", and enter your API token.

Once added, pick **Muse** as the conversation agent for your voice
assistant under **Settings > Voice assistants**.

## Layout

```
custom_components/muse_conversation/
├── __init__.py        # config entry setup / unload
├── manifest.json      # integration metadata
├── config_flow.py     # token setup UI
├── conversation.py    # ConversationEntity: the assistant itself
├── muse_client.py     # transport to Muse (stub; implement here)
├── const.py
├── strings.json
└── translations/en.json
```

## Notes

- Your Home Assistant fork at `~/git/home-assistant-core` is stale (it sits
  at 0.116, from 2020). This integration targets the modern conversation
  entity API, so develop against a current checkout or just drop it into
  your running HA.
- The stub raises a clear error through the voice pipeline if Muse can't be
  reached, so failures show up as spoken replies instead of silence.
