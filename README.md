# Samsung Soundbar Local IP Control (N950)

Local HTTP control and test harness for Samsung Soundbar models using the Samsung Multiroom/WAM UIC API.

This repository is now focused on:
- A practical local test harness
- A curated command set with known behavior
- Clean documentation of what works on tested firmware

## Scope

- Protocol: XML-over-HTTP (`/UIC?cmd=`)
- Tested host/port: `192.168.1.5:56001`
- Device tested: Samsung N950 (firmware-dependent behavior expected)

## Quick Start (Local Harness)

Run from repo root:

```bash
python3 app.py
```

Open:

```text
http://127.0.0.1:8787
```

The harness supports:
- Save IP/port
- Confirm connectivity
- Add/edit/delete commands
- Test commands and mark working/not working
- Persist command status in `data/commands.json`

## API Pattern Reference

Base URL:

```text
http://<IP>:56001/UIC?cmd=<urlencoded_xml>
```

Common XML patterns:

```xml
<name>MethodName</name>
<p type="dec" name="variable" val="123"/>
<p type="str" name="variable" val="value"/>
<p type="cdata" name="variable" val="empty"><![CDATA[text]]></p>
```

## Confirmed Working Commands

### Core Status

- `GetFeature`
  - `<name>GetFeature</name>`
- `GetPowerStatus`
  - `<name>GetPowerStatus</name>`
- `GetVolume`
  - `<name>GetVolume</name>`
- `GetMute`
  - `<name>GetMute</name>`
- `GetFunc`
  - `<name>GetFunc</name>`

### Volume

- Absolute set (recommended)
  - `<name>SetVolume</name><p type="dec" name="volume" val="10"/>`
- Alternate absolute set using `delta` field (device-specific behavior)
  - `<name>SetVolume</name><p type="dec" name="delta" val="10"/>`

Note: on this N950, `delta` behaves as an absolute target, not relative step.

### Input Selection

- HDMI1
  - `<name>SetFunc</name><p type="str" name="function" val="hdmi1"/>`
- HDMI2
  - `<name>SetFunc</name><p type="str" name="function" val="hdmi2"/>`
- Optical
  - `<name>SetFunc</name><p type="str" name="function" val="optical"/>`
- ARC
  - `<name>SetFunc</name><p type="str" name="function" val="arc"/>`
- Bluetooth
  - `<name>SetFunc</name><p type="str" name="function" val="bt"/>`

### Mute

- Mute on
  - `<name>SetMute</name><p type="str" name="mute" val="on"/>`
- Mute off
  - `<name>SetMute</name><p type="str" name="mute" val="off"/>`

### Woofer

- Get woofer level
  - `<name>GetWooferLevel</name>`
- Set woofer to `+6`
  - `<name>SetWooferLevel</name><p type="dec" name="wooferlevel" val="6"/>`
- Set woofer to `-6`
  - `<name>SetWooferLevel</name><p type="dec" name="wooferlevel" val="-6"/>`

### EQ / Sound Mode

- `<name>GetSoundMode</name>`
- `<name>Get7BandEQList</name>`
- `<name>GetCurrentEQMode</name>`
- `<name>Set7bandEQMode</name><p type="dec" name="presetindex" val="1"/>`
- `<name>Set7bandEQValue</name>` with `presetindex` + `eqvalue1..eqvalue7`

Example:

```xml
<name>Set7bandEQValue</name>
<p type="dec" name="presetindex" val="4"/>
<p type="dec" name="eqvalue1" val="0"/>
<p type="dec" name="eqvalue2" val="0"/>
<p type="dec" name="eqvalue3" val="0"/>
<p type="dec" name="eqvalue4" val="0"/>
<p type="dec" name="eqvalue5" val="0"/>
<p type="dec" name="eqvalue6" val="0"/>
<p type="dec" name="eqvalue7" val="0"/>
```

### Device Info

- `<name>GetApInfo</name>`
- `<name>GetMainInfo</name>`

## Known Unreliable / Not Working (Current Firmware)

- `<name>PowerOn</name>`
- `<name>PowerOff</name>`
- `<name>VolumeUp</name>`
- `<name>VolumeDown</name>`
- `<name>GetEQBalance</name>`

`SetPowerStatus` with `power=0` may respond with `ok` but has been flaky in repeated validation.

## What `GetFeature` Tells Us on This N950

Observed enabled capabilities include:
- `arc=1`, `bt=1`, `din=1`
- `numofhdmi=2`
- `wifidlna=1`, `miracast=1`, `multiroommc=1`, `multiroomms=1`
- `wooferoption=2`

Observed disabled/not present:
- `aux=0`, `usb=0`

## Data Files

- `data/config.json`: harness target IP/port
- `data/commands.json`: curated command list and statuses

## Changelog

### 2026-03-03
- Added local web command harness (`app.py`, `web/`)
- Added command add/edit/delete/test workflow
- Curated and cleaned command set in `data/commands.json`
- Removed brute-force discovery artifacts and temporary research scripts
- Rewrote documentation as a working command reference

## Disclaimer

This project is based on reverse engineering and model-specific behavior. Command support varies by firmware and device family. Use at your own risk.
