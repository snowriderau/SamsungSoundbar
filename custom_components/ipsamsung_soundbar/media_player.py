from __future__ import annotations

from urllib.parse import quote
import xml.etree.ElementTree as ET

from aiohttp import ClientError

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_NAME, DEFAULT_NAME, DEFAULT_PORT, DOMAIN, SOURCE_LIST

SUPPORTED_FEATURES = (
    MediaPlayerEntityFeature.TURN_ON
    | MediaPlayerEntityFeature.TURN_OFF
    | MediaPlayerEntityFeature.VOLUME_SET
    | MediaPlayerEntityFeature.VOLUME_STEP
    | MediaPlayerEntityFeature.VOLUME_MUTE
    | MediaPlayerEntityFeature.SELECT_SOURCE
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    host = entry.data[CONF_HOST]
    port = entry.data.get(CONF_PORT, DEFAULT_PORT)
    name = entry.data.get(CONF_NAME, DEFAULT_NAME)
    async_add_entities([SamsungSoundbarEntity(hass, host, port, name)], True)


class SamsungSoundbarEntity(MediaPlayerEntity):
    _attr_supported_features = SUPPORTED_FEATURES
    _attr_icon = "mdi:soundbar"

    def __init__(self, hass: HomeAssistant, host: str, port: int, name: str) -> None:
        self.hass = hass
        self._host = host
        self._port = port
        self._attr_name = name
        self._attr_unique_id = f"{DOMAIN}_{host}_{port}"
        self._attr_source_list = SOURCE_LIST
        self._attr_state = MediaPlayerState.OFF
        self._attr_volume_level = None
        self._attr_is_volume_muted = None
        self._attr_source = None

    def _url(self, xml_payload: str) -> str:
        return f"http://{self._host}:{self._port}/UIC?cmd={quote(xml_payload, safe='')}"

    async def _request(self, xml_payload: str) -> ET.Element | None:
        session = async_get_clientsession(self.hass)
        try:
            async with session.get(self._url(xml_payload), timeout=4) as resp:
                if resp.status != 200:
                    return None
                text = await resp.text()
                return ET.fromstring(text)
        except (TimeoutError, ClientError, ET.ParseError):
            return None

    async def _send(self, xml_payload: str) -> bool:
        root = await self._request(xml_payload)
        if root is None:
            return False
        response = root.find(".//response")
        return response is not None and response.attrib.get("result") == "ok"

    async def async_update(self) -> None:
        vol_root = await self._request("<name>GetVolume</name>")
        if vol_root is not None:
            vol_text = vol_root.findtext(".//volume")
            if vol_text is not None and vol_text.isdigit():
                self._attr_volume_level = max(0.0, min(1.0, int(vol_text) / 100.0))

        mute_root = await self._request("<name>GetMute</name>")
        if mute_root is not None:
            mute_text = mute_root.findtext(".//mute")
            if mute_text is not None:
                self._attr_is_volume_muted = mute_text.lower() == "on"

        func_root = await self._request("<name>GetFunc</name>")
        if func_root is not None:
            func_text = func_root.findtext(".//function")
            if func_text:
                self._attr_source = func_text

        power_root = await self._request("<name>GetPowerStatus</name>")
        if power_root is not None:
            power = power_root.findtext(".//powerStatus")
            if power == "1":
                self._attr_state = MediaPlayerState.ON
            elif power == "0":
                self._attr_state = MediaPlayerState.OFF
            else:
                self._attr_state = MediaPlayerState.ON
        else:
            # Device often stops responding when off; keep optimistic ON state if reachable by other calls.
            self._attr_state = MediaPlayerState.ON

    async def async_turn_on(self) -> None:
        if await self._send("<name>PowerOn</name>"):
            self._attr_state = MediaPlayerState.ON

    async def async_turn_off(self) -> None:
        # Try native PowerOff first, then SetPowerStatus fallback.
        ok = await self._send("<name>PowerOff</name>")
        if not ok:
            ok = await self._send('<name>SetPowerStatus</name><p type="dec" name="power" val="0"/>')
        if ok:
            self._attr_state = MediaPlayerState.OFF

    async def async_set_volume_level(self, volume: float) -> None:
        value = int(max(0, min(100, round(volume * 100))))
        if await self._send(f'<name>SetVolume</name><p type="dec" name="volume" val="{value}"/>'):
            self._attr_volume_level = value / 100.0

    async def async_volume_up(self) -> None:
        if self._attr_volume_level is None:
            await self.async_update()
        current = int((self._attr_volume_level or 0) * 100)
        target = min(100, current + 1)
        await self.async_set_volume_level(target / 100.0)

    async def async_volume_down(self) -> None:
        if self._attr_volume_level is None:
            await self.async_update()
        current = int((self._attr_volume_level or 0) * 100)
        target = max(0, current - 1)
        await self.async_set_volume_level(target / 100.0)

    async def async_mute_volume(self, mute: bool) -> None:
        value = "on" if mute else "off"
        if await self._send(f'<name>SetMute</name><p type="str" name="mute" val="{value}"/>'):
            self._attr_is_volume_muted = mute

    async def async_select_source(self, source: str) -> None:
        if source not in SOURCE_LIST:
            return
        if await self._send(f'<name>SetFunc</name><p type="str" name="function" val="{source}"/>'):
            self._attr_source = source
