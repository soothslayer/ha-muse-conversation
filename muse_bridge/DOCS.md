# Muse Bridge

Runs Muse's paired gadget connection on Home Assistant OS. Use the Muse
Conversation integration and the Voice PE's official HA firmware for speech.
No separate computer or external TTS relay is needed.

For the complete installation, Assist configuration, and speaker checks, follow
the [Home Assistant OS + Voice PE guide](../README.md#set-up-home-assistant-os-and-voice-pe).

## Setup

1. In **Settings > Apps > App store > Repositories**, add
   `https://github.com/soothslayer/ha-muse-conversation`, then install **Muse Bridge**.
   On older HA versions, Apps is called Add-ons.
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

During setup, a temporary BlueZ agent handles iPhone Bluetooth pairing only
for the peer writing the Muse GATT setup characteristic. It rejects unrelated
services and devices, does not mark phones trusted, and restores the adapter's
pairability settings when setup ends. iPhone pairing, credential provisioning, and Muse registration have been
verified on HA OS 18.3. Discovery alone does not prove setup completed.

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

This is experimental. **Raspberry Pi users should use HA OS 18.3 or newer
for Bluetooth pairing.** HA OS 18.2 uses a kernel with the advertising length
validation regression discussed in [BlueZ issue 2269](https://github.com/bluez/bluez/issues/2269).
The kernel source shipped by HA OS 18.3 contains the backward-compatibility
correction. Setting the advertisement's discoverable flag alone does not fix it.
Upgrading the test Raspberry Pi host from 18.2 to 18.3 restored successful
GATT registration and Bluetooth advertising with the same bridge version.

Voice PE playback through HA TTS and the paired Muse cloud connection have
been verified. Muse receives test messages and replies in the phone app;
new-chat and follow-up replies return through the bridge, and Assist text
responses work. The device owner also confirmed the complete PE microphone →
Assist → Muse → spoken reply flow. An expired or revoked backup pairing cannot replace fresh
phone pairing; migration only works while the original refresh token is valid.

## Updating a preview installation

If you installed a preview using a repository URL ending in
`#feat/assist-spoken-replies`, keep that source available until you migrate the
installation. Changing a repository URL can create a separate app-store entry;
do not uninstall a working paired bridge just to change its source.
New installations should use the branch-free repository URL in the setup steps.

## Migrate an existing gadget

If a gadget has been retired or flashed with HA firmware, its saved Muse
pairing can be migrated instead of pairing the HA Bluetooth adapter again.
Only do this with your own backup, and keep the old Muse firmware stopped.

Place a mode-0600 `pairing-import.json` in `/share/muse-conversation` with
`identity.mac` set to the original gadget's lowercase MAC and `pairing`
containing its `access_token`, `refresh_token`, and any original `api_url_v2`
or `noise_host`. Do not substitute a different device identity. The app
imports this into private data, forces token refresh, and deletes the import
file. It refuses to overwrite an already paired app. Never put this file in
a repository, terminal history, or a support log.
