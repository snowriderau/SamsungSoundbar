# Samsung WAM/UIC Command Reference (Extension Guide)

This document is intended for contributors extending support for additional Samsung soundbars and firmware variants.

## Protocol Basics

- Base endpoint:
  - `http://<IP>:56001/UIC?cmd=<urlencoded_xml>`
- Some models/firmware may use `55001` instead.
- Commands are XML payloads in `cmd` query param.

## XML Payload Patterns

### Method only

```xml
<name>GetFeature</name>
```

### Integer parameter (`dec`)

```xml
<name>SetVolume</name>
<p type="dec" name="volume" val="10"/>
```

### String parameter (`str`)

```xml
<name>SetFunc</name>
<p type="str" name="function" val="hdmi1"/>
```

### CDATA parameter (`cdata`)

```xml
<name>SetSpkName</name>
<p type="cdata" name="spkname" val="empty"><![CDATA[Living Room]]></p>
```

## Reliability Categories (N950 Testing)

### Confirmed reliable

- `GetFeature`
- `GetPowerStatus`
- `GetVolume`
- `SetVolume` (`dec`, `name=volume`, absolute target)
- `GetMute`
- `SetMute` (`str`, `name=mute`, `on/off`)
- `GetFunc`
- `SetFunc` (`str`, `name=function`, values like `hdmi1`, `hdmi2`, `optical`, `arc`, `bt`)
- `GetWooferLevel`
- `SetWooferLevel` (`dec`, `name=wooferlevel`, tested `-6..6`)
- `Get7BandEQList`
- `GetCurrentEQMode`
- `Set7bandEQMode` (`dec`, `name=presetindex`)
- `Set7bandEQValue` (`dec`, `presetindex` + `eqvalue1..eqvalue7`)
- `GetApInfo`
- `GetMainInfo`

### Known unreliable / firmware dependent

- `PowerOn`
- `PowerOff`
- `VolumeUp`
- `VolumeDown`
- `SetPowerStatus` (some values respond but repeatability is inconsistent)

### Not working in current testing

- `GetEQBalance`
- `GetBass` / `SetBass`
- `GetTreble` / `SetTreble`

## Feature Discovery (Recommended First Step)

Run:

```bash
curl 'http://<IP>:56001/UIC?cmd=%3Cname%3EGetFeature%3C/name%3E'
```

The response often tells you which capabilities are exposed on the current device:
- inputs (`numofhdmi`, input modes)
- transport/network flags (`wifidlna`, `miracast`, `multiroom*`)
- woofer support (`wooferoption`)

## Method Families Seen Across WAM Docs/Libraries

Common `Get*` families:
- Device/system: `GetFeature`, `GetMainInfo`, `GetApInfo`, `GetSoftwareVersion`, `GetSubSoftwareVersion`
- Audio state: `GetVolume`, `GetMute`, `GetFunc`, `GetPowerStatus`, `GetSoundMode`, `GetWooferLevel`
- EQ: `Get7BandEQList`, `GetCurrentEQMode`
- Queue/playback: `GetPlayStatus`, `GetMusicInfo`, `GetCurrentPlayTime`, `GetCurrentPlaylist`

Common `Set*` families:
- Core control: `SetVolume`, `SetMute`, `SetFunc`
- EQ/woofer: `SetWooferLevel`, `Set7bandEQMode`, `Set7bandEQValue`
- Playback/radio/service methods exist on many speakers but may not apply to soundbars.

## Practical Extension Workflow

1. Check `GetFeature` and `GetMainInfo` first.
2. Prefer `Get*` methods to map capability and response schema.
3. For `Set*`, start with known parameter name/type from community references.
4. Treat `response result="ok"` as provisional; verify state actually changed using follow-up `Get*`.
5. Save proven commands in `data/commands.json` with status.

## Safety Notes

- Avoid network/config mutators (for example, IP/network setup commands) during normal probing.
- Keep timeout short and retry limited; some invalid methods can stall.

## References

- [WAM API Methods](https://github.com/bacl/WAM_API_DOC/blob/master/API_Methods.md)
- [samsung_multiroom library](https://github.com/krygal/samsung_multiroom)
- [pywam / samsungwam](https://github.com/Strixx76/samsungwam)
