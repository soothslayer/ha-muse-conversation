# Muse Bridge

Runs Muse's paired gadget connection on Home Assistant OS. Use the Muse
Conversation integration and the Voice PE's official HA firmware for speech.
No separate computer or external TTS relay is needed.

## Setup

1. Add this repository to the Home Assistant app store. While this change is
   in a draft PR, copy this `muse_bridge` folder into `/addons/muse_bridge`,
   reload the store, and install the local Muse Bridge app.
2. Set `sdk_token` in the app configuration to your gadget SDK token from
   https://gadgets.muse.ai. This is distinct from a device pairing token.
3. Start the app and read its log for the `MuseGadget...` Bluetooth name.
4. Near the Home Assistant host, use Muse phone app **Settings > Devices >
   Add device**. Choose that name and use its existing network connection.
   Pairing remains open for ten minutes. Restart the app to retry.
5. Install the Muse Conversation custom integration and restart HA. Add the
   integration using `/share/muse-conversation/musegadget.sock`.
6. Select Muse as your Assist conversation agent, configure speech-to-text
   and text-to-speech, and assign the pipeline to your Voice PE.

The HA host needs a working local Bluetooth adapter accessible through BlueZ
D-Bus. An ESPHome Bluetooth proxy does not replace it. AppArmor protection
remains enabled. Pairing credentials survive restarts in private `/data`.
The app publishes only a local Unix socket; it has no HTTP port and cannot
execute shell/file commands for Muse.

For private credential migration, a token file at
`/share/muse-conversation/sdk_token` is imported into private app data and
removed after validation on startup. Prefer the password configuration field
for normal setup. Treat HA backups as sensitive because they include pairing.

## Troubleshooting

If pairing stalls, check the app log for Bluetooth/GATT errors and confirm
the phone is near the HA host. If the log says pairing was removed, restart
the app and pair it again. Do not turn off HA Bluetooth protection globally.

A local socket connection only confirms that the bridge is running; the Muse
session also needs to be connected. A read-only status request is supported:
`{"operation":"status"}` returns `connected` and `reply_support` booleans.

This is experimental. Automated tests cover reply handling; live HA OS
Bluetooth pairing and Voice PE playback must be tested on the target host.
