# Brute Force Summary (2026-03-03T04:41:09.228324+00:00)

Target: `192.168.1.5:56001`
Total tested: **102**
Working: **29**
Recognized but rejected: **11**
Transport error/timeouts: **62**

## Working Commands
- `Get7BandEQList` -> `<name>Get7BandEQList</name>`
- `GetAcmMode` -> `<name>GetAcmMode</name>`
- `GetAlarmInfo` -> `<name>GetAlarmInfo</name>`
- `GetAlarmSoundList` -> `<name>GetAlarmSoundList</name>`
- `GetApInfo` -> `<name>GetApInfo</name>`
- `GetAudioUI` -> `<name>GetAudioUI</name>`
- `GetAutoUpdate` -> `<name>GetAutoUpdate</name>`
- `GetAvSourceAll` -> `<name>GetAvSourceAll</name>`
- `GetCandidateSpkList` -> `<name>GetCandidateSpkList</name>`
- `GetCurrentEQMode` -> `<name>GetCurrentEQMode</name>`
- `GetFeature` -> `<name>GetFeature</name>`
- `GetFunc` -> `<name>GetFunc</name>`
- `GetGroupName` -> `<name>GetGroupName</name>`
- `GetMainInfo` -> `<name>GetMainInfo</name>`
- `GetMute` -> `<name>GetMute</name>`
- `GetPowerStatus` -> `<name>GetPowerStatus</name>`
- `GetSleepTimer` -> `<name>GetSleepTimer</name>`
- `GetSoftwareVersion` -> `<name>GetSoftwareVersion</name>`
- `GetSpeakerBuyer` -> `<name>GetSpeakerBuyer</name>`
- `GetSpeakerWifiRegion` -> `<name>GetSpeakerWifiRegion</name>`
- `GetSpkName` -> `<name>GetSpkName</name>`
- `GetSubSoftwareVersion` -> `<name>GetSubSoftwareVersion</name>`
- `GetVolume` -> `<name>GetVolume</name>`
- `GetWooferLevel` -> `<name>GetWooferLevel</name>`
- `SetWooferLevel` -> `<name>SetWooferLevel</name><p type="dec" name="wooferlevel" val="6"/>`
- `SetWooferLevel` -> `<name>SetWooferLevel</name><p type="dec" name="wooferlevel" val="-6"/>`
- `GetSoundMode` -> `<name>GetSoundMode</name>`
- `Set7bandEQMode` -> `<name>Set7bandEQMode</name><p type="dec" name="presetindex" val="1"/>`
- `Set7bandEQValue` -> `<name>Set7bandEQValue</name><p type="dec" name="presetindex" val="4"/><p type="dec" name="eqvalue1" val="0"/><p type="dec" name="eqvalue2" val="0"/><p type="dec" name="eqvalue3" val="0"/><p type="dec" name="eqvalue4" val="0"/><p type="dec" name="eqvalue5" val="0"/><p type="dec" name="eqvalue6" val="0"/><p type="dec" name="eqvalue7" val="0"/>`

## Recognized But Rejected
- `Set7bandEQMode` (Invalid parameter number) -> `<name>Set7bandEQMode</name>`
- `Set7bandEQValue` (Invalid parameter number) -> `<name>Set7bandEQValue</name>`
- `SetAlarmInfo` (Invalid parameter number) -> `<name>SetAlarmInfo</name>`
- `SetAlarmOnOff` (Invalid parameter number) -> `<name>SetAlarmOnOff</name>`
- `SetFunc` (Invalid parameter number) -> `<name>SetFunc</name>`
- `SetMute` (Invalid parameter number) -> `<name>SetMute</name>`
- `SetSleepTimer` (Invalid parameter number) -> `<name>SetSleepTimer</name>`
- `SetSpeakerTime` (Invalid parameter number) -> `<name>SetSpeakerTime</name>`
- `SetVolume` (Invalid parameter number) -> `<name>SetVolume</name>`
- `SetWooferLevel` (Invalid parameter number) -> `<name>SetWooferLevel</name><p type="int" name="woofer" val="6"/>`
- `SetWooferLevel` (Invalid parameter number) -> `<name>SetWooferLevel</name><p type="int" name="woofer" val="-6"/>`
