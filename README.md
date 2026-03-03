# Samsung Soundbar Local IP (Home Assistant HACS Integration)

Local-only Home Assistant integration for Samsung soundbars using the WAM/UIC HTTP API.

## Status

This repository is now structured as a proper HACS custom integration:

- `custom_components/ipsamsung_soundbar/`
- Config flow enabled
- Media player platform registered correctly

## HACS Installation

1. In HACS, add this repository as a **Custom repository**.
2. Category: **Integration**.
3. Install **Samsung Soundbar Local IP**.
4. Restart Home Assistant.
5. Go to **Settings -> Devices & Services -> Add Integration**.
6. Search for **Samsung Soundbar Local IP**.
7. Enter:
   - Host/IP (example: `192.168.1.5`)
   - Port (default: `56001`)
   - Name

## What This Integration Supports

- Power: `turn_on`, `turn_off` (soundbar firmware dependent)
- Volume:
  - Set absolute volume (`0-100`)
  - Volume up/down (implemented as absolute +/-1)
- Mute: on/off
- Source select:
  - `hdmi1`, `hdmi2`, `optical`, `arc`, `bt`
- Polling state:
  - power status
  - volume
  - mute
  - source

## Command Behavior Notes (N950 Testing)

Reliable:
- `<name>GetVolume</name>`
- `<name>SetVolume</name><p type="dec" name="volume" val="N"/>`
- `<name>GetMute</name>`
- `<name>SetMute</name><p type="str" name="mute" val="on|off"/>`
- `<name>GetFunc</name>`
- `<name>SetFunc</name><p type="str" name="function" val="hdmi1|hdmi2|optical|arc|bt"/>`

Less reliable (firmware dependent):
- `<name>PowerOn</name>`
- `<name>PowerOff</name>`

The integration attempts power fallback logic when possible.

## Local Harness (Optional)

A local command harness is also included for research/testing:

```bash
python3 app.py
```

Then open `http://127.0.0.1:8787`.

## Troubleshooting

If the integration still does not load in Home Assistant:

1. Confirm files exist under:
   - `custom_components/ipsamsung_soundbar/manifest.json`
   - `custom_components/ipsamsung_soundbar/__init__.py`
   - `custom_components/ipsamsung_soundbar/media_player.py`
2. Restart Home Assistant after install/update.
3. Check **Settings -> System -> Logs** for `ipsamsung_soundbar` errors.
4. Confirm the soundbar responds on `56001`:

```bash
curl 'http://<IP>:56001/UIC?cmd=%3Cname%3EGetFeature%3C/name%3E'
```

## Disclaimer

This is an unofficial reverse-engineered integration. Command support varies by soundbar model and firmware.
