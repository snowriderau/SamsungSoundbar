# Home Assistant Local IP Control of Samsung Soundbar
FYI Testing Still in Progress.

This repository contains a custom Home Assistant component for locally controlling your Samsung Soundbar over your home network without the need for Samsung’s SmartThings API. The following commands have been tested on my device and can be used to query or control key functions.

Note: These commands are based on reverse engineering and testing on one specific soundbar. Your device may have different firmware or command support. Use at your own risk.

**Tested Functions and Example URLs**
Replace <IP_ADDRESS> with the IP address of your Samsung Soundbar and ensure the port is correct (default is 56001).

**Power Control**
Turn On
Command: <name>PowerOn</name>
Example URL:
http://<IP_ADDRESS>:56001/UIC?cmd=%3Cname%3EPowerOn%3C/name%3E

**Turn Off**
Command: <name>PowerOff</name>
Example URL:
http://<IP_ADDRESS>:56001/UIC?cmd=%3Cname%3EPowerOff%3C/name%3E

**Volume Control**
Get Volume
Command: <name>GetVolume</name>
Example URL:
http://<IP_ADDRESS>:56001/UIC?cmd=%3Cname%3EGetVolume%3C/name%3E

**Set Volume** Working
Command: <name>SetVolume</name><p type="int" name="volume" val="XX"/>
Replace XX with a two-digit number (e.g., 20 for volume 20).
Example URL:
http://<IP_ADDRESS>:56001/UIC?cmd=%3Cname%3ESetVolume%3C/name%3E%3Cp%20type=%22int%22%20name=%22volume%22%20val=%2220%22/%3E

**Mute Control** Working
Get Mute Status
Command: <name>GetMute</name>
Example URL:
http://<IP_ADDRESS>:56001/UIC?cmd=%3Cname%3EGetMute%3C/name%3E

**Set Mute** Working
Command: <name>SetMute</name><p type="str" name="mute" val="on/off"/>
Replace on/off with the desired mute state.
Example URL (Unmute):
http://<IP_ADDRESS>:56001/UIC?cmd=%3Cname%3ESetMute%3C/name%3E%3Cp%20type=%22str%22%20name=%22mute%22%20val=%22off%22/%3E

**Input / Function** Working
Get Input Function
Command: <name>GetFunc</name>
Example URL:
http://<IP_ADDRESS>:56001/UIC?cmd=%3Cname%3EGetFunc%3C/name%3E

Set Input Function
Command: <name>SetFunc</name><p type="str" name="function" val="INPUT"/>
Replace INPUT with the desired input (e.g., hdmi1, hdmi2, etc.).
Example URL:
http://<IP_ADDRESS>:56001/UIC?cmd=%3Cname%3ESetFunc%3C/name%3E%3Cp%20type=%22str%22%20name=%22function%22%20val=%22hdmi1%22/%3E

**Sound Mode and Woofer Level**
Get Sound Mode
Command: <name>GetSoundMode</name>
Example URL:
http://<IP_ADDRESS>:56001/UIC?cmd=%3Cname%3EGetSoundMode%3C/name%3E

**Get Woofer Level** Working
Command: <name>GetWooferLevel</name>
Example URL:
http://<IP_ADDRESS>:56001/UIC?cmd=%3Cname%3EGetWooferLevel%3C/name%3E

# Usage
Configure Your Device:**
In your Home Assistant configuration.yaml, add an entry for the SamsungSoundbar component with the appropriate host, port, and name:

**yaml**
Copy
media_player:
  - platform: samsung_soundbar
    host: 192.168.1.5
    port: 56001
    name: Living Room Soundbar

    
# Testing Commands:
You can test the commands by accessing the URLs above in your web browser or via tools like curl or Postman. Ensure your device is on the same network.

# Review Logs:
Check Home Assistant’s logs to see detailed debug information about the commands and responses.

# Contributing
Contributions and improvements are welcome! If you discover additional commands or improvements, feel free to submit an issue or a pull request.

# Disclaimer
This component and the commands listed here are provided as-is, based on testing with a specific model of Samsung Soundbar. Compatibility with other models is not guaranteed. Use at your own risk.

Happy automating!

## Latest Harness Results (March 3, 2026)

The local test harness in this repo (`app.py` + `data/commands.json`) was used to validate command behavior on-device.

### Confirmed working

- `GetVolume`
  - `<name>GetVolume</name>`
- `SetVolume` (HTTP responds, payload behavior should be model-verified)
  - `<name>SetVolume</name><p type="int" name="volume" val="20"/>`
- `GetMute`
  - `<name>GetMute</name>`
- `SetMute` (off)
  - `<name>SetMute</name><p type="str" name="mute" val="off"/>`
- `GetFunc`
  - `<name>GetFunc</name>`
- `SetFunc` (hdmi1)
  - `<name>SetFunc</name><p type="str" name="function" val="hdmi1"/>`
- `GetApInfo`
  - `<name>GetApInfo</name>`
- `GetSpeakerStatus`
  - `<name>GetSpeakerStatus</name>`

### Currently not working (timed out during testing)

- `PowerOn`
  - `<name>PowerOn</name>`
- `PowerOff`
  - `<name>PowerOff</name>`
- `GetEQBalance`
  - `<name>GetEQBalance</name>`

## Brute-Force Discovery Run (March 3, 2026)

A scripted probe was run against `192.168.1.5:56001` using command names sourced from community WAM repos (`WAM_API_DOC`, `samsung_multiroom`, `pywam`) plus targeted soundbar guesses.

- Total tested: `102`
- Working: `29`
- Recognized but rejected (wrong/missing parameters): `11`
- Timeout/no response: `62`

Artifacts:
- `data/discovered_command_names.txt`
- `scripts/bruteforce_wam_commands.py`
- `data/bruteforce_results.json`
- `data/bruteforce_summary.md`

### Confirmed Woofer / EQ Commands

- Woofer get:
  - `<name>GetWooferLevel</name>`
- Woofer set (`-6` to `+6` works with `dec` + `wooferlevel`):
  - `<name>SetWooferLevel</name><p type="dec" name="wooferlevel" val="-6"/>`
  - `<name>SetWooferLevel</name><p type="dec" name="wooferlevel" val="6"/>`
- EQ mode list / active mode:
  - `<name>Get7BandEQList</name>`
  - `<name>GetCurrentEQMode</name>`
- EQ mode set (example):
  - `<name>Set7bandEQMode</name><p type="dec" name="presetindex" val="1"/>`
- 7-band EQ value set (example):
  - `<name>Set7bandEQValue</name><p type="dec" name="presetindex" val="4"/><p type="dec" name="eqvalue1" val="0"/><p type="dec" name="eqvalue2" val="0"/><p type="dec" name="eqvalue3" val="0"/><p type="dec" name="eqvalue4" val="0"/><p type="dec" name="eqvalue5" val="0"/><p type="dec" name="eqvalue6" val="0"/><p type="dec" name="eqvalue7" val="0"/>`

### Bass / Treble

`GetBass`, `SetBass`, `GetTreble`, and `SetTreble` timed out on this device/firmware during this run. That suggests these names are not exposed on this model, or require a different command family/endpoint.

## Local Web Test Harness

This repo now includes a simple local web app to test and track Samsung soundbar commands.

### Files added
- `app.py`: local backend server and API
- `web/index.html`: UI
- `web/styles.css`: UI styles
- `web/app.js`: UI logic
- `data/config.json`: saved soundbar IP + port
- `data/commands.json`: command list and test outcomes

### Start the harness

From this repo root:

```bash
python3 app.py
```

Then open:

```text
http://127.0.0.1:8787
```

### What it does

- Enter soundbar IP + port and save.
- Confirm if the soundbar responds to known probe commands.
- View the command list.
- Test a command and automatically mark it working/not working.
- Manually set working/not working.
- Add a command.
- Delete a command.
- Persist all updates to `data/commands.json`.

### API summary

- `GET /api/config`
- `POST /api/config`
- `POST /api/ping`
- `GET /api/commands`
- `POST /api/commands`
- `POST /api/commands/{id}/test`
- `POST /api/commands/{id}/status`
- `DELETE /api/commands/{id}`
