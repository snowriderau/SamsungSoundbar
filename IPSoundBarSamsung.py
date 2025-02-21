from __future__ import annotations

import asyncio
import logging
import async_timeout
import xml.etree.ElementTree as ET
import aiohttp
import voluptuous as vol

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    PLATFORM_SCHEMA,
)
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "Samsung Soundbar"
DEFAULT_PORT = 56001

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional("port", default=DEFAULT_PORT): int,
})

SUPPORT_SAMSUNG = (
    MediaPlayerEntityFeature.VOLUME_SET
    | MediaPlayerEntityFeature.VOLUME_MUTE
    | MediaPlayerEntityFeature.TURN_ON
    | MediaPlayerEntityFeature.TURN_OFF
    | MediaPlayerEntityFeature.VOLUME_STEP
    | MediaPlayerEntityFeature.SELECT_SOURCE
)

class SamsungSoundbar(MediaPlayerEntity):
    _attr_supported_features = SUPPORT_SAMSUNG
    _attr_icon = "mdi:soundbar"

    def __init__(self, config: dict, session: aiohttp.ClientSession) -> None:
        self._attr_name = config[CONF_NAME]
        self._host = config[CONF_HOST]
        self._port = config.get("port", DEFAULT_PORT)
        self._session = session
        self._base_url = f"http://{self._host}:{self._port}/UIC?cmd="
        self._attr_state = MediaPlayerState.OFF
        self._attr_volume_level = 0.0
        self._attr_is_volume_muted = False
        self._attr_source = None
        # Define a list of valid input sources (adjust as needed)
        self._source_list = ["hdmi1", "hdmi2", "optical", "bluetooth"]

    @property
    def source_list(self) -> list[str]:
        return self._source_list

    async def async_update(self) -> None:
        """Retrieve the latest state from the soundbar by polling it."""
        await asyncio.gather(
            self._async_get_volume(),
            self._async_get_mute(),
            self._async_get_func(),
            self._async_get_sound_mode(),
            self._async_get_woofer_level()
        )

    async def _fetch_xml(self, command: str) -> ET.Element | None:
        """Send an HTTP GET request and parse the XML response."""
        url = self._base_url + command
        try:
            async with async_timeout.timeout(10):
                async with self._session.get(url) as response:
                    text = await response.text()
                    return ET.fromstring(text)
        except Exception as e:
            _LOGGER.error("Error fetching command %s: %s", command, e)
            return None

    async def _async_get_volume(self) -> None:
        # Command: <name>GetVolume</name>
        command = "%3Cname%3EGetVolume%3C/name%3E"
        root = await self._fetch_xml(command)
        if root is not None:
            volume_elem = root.find(".//volume")
            if volume_elem is not None and volume_elem.text.isdigit():
                volume = int(volume_elem.text)
                self._attr_volume_level = volume / 100.0
                _LOGGER.debug("Volume updated: %s", volume)

    async def _async_get_mute(self) -> None:
        # Command: <name>GetMute</name>
        command = "%3Cname%3EGetMute%3C/name%3E"
        root = await self._fetch_xml(command)
        if root is not None:
            mute_elem = root.find(".//mute")
            if mute_elem is not None:
                self._attr_is_volume_muted = (mute_elem.text.lower() == "on")
                _LOGGER.debug("Mute updated: %s", mute_elem.text)

    async def _async_get_func(self) -> None:
        # Command: <name>GetFunc</name>
        command = "%3Cname%3EGetFunc%3C/name%3E"
        root = await self._fetch_xml(command)
        if root is not None:
            func_elem = root.find(".//function")
            if func_elem is not None:
                self._attr_source = func_elem.text
                _LOGGER.debug("Source updated: %s", func_elem.text)

    async def _async_get_sound_mode(self) -> None:
        # Command: <name>GetSoundMode</name>
        command = "%3Cname%3EGetSoundMode%3C/name%3E"
        root = await self._fetch_xml(command)
        if root is not None:
            mode_elem = root.find(".//soundMode")
            if mode_elem is not None:
                _LOGGER.debug("Sound mode: %s", mode_elem.text)

    async def _async_get_woofer_level(self) -> None:
        # Command: <name>GetWooferLevel</name>
        command = "%3Cname%3EGetWooferLevel%3C/name%3E"
        root = await self._fetch_xml(command)
        if root is not None:
            level_elem = root.find(".//level")
            if level_elem is not None:
                _LOGGER.debug("Woofer level: %s", level_elem.text)

    async def async_turn_on(self) -> None:
        """Turn the soundbar on."""
        command = "%3Cname%3EPowerOn%3C/name%3E"
        await self._fetch_xml(command)
        self._attr_state = MediaPlayerState.ON

    async def async_turn_off(self) -> None:
        """Turn the soundbar off."""
        command = "%3Cname%3EPowerOff%3C/name%3E"
        await self._fetch_xml(command)
        self._attr_state = MediaPlayerState.OFF

    async def async_set_volume_level(self, volume: float) -> None:
        """Set the volume level (0.0 to 1.0)."""
        vol_value = int(round(volume * 100))
        command = (
            f"%3Cname%3ESetVolume%3C/name%3E"
            f"%3Cp%20type=%22int%22%20name=%22volume%22%20val=%22{vol_value}%22/%3E"
        )
        await self._fetch_xml(command)
        self._attr_volume_level = volume

    async def async_mute_volume(self, mute: bool) -> None:
        """Mute or unmute the soundbar."""
        mute_val = "on" if mute else "off"
        command = (
            f"%3Cname%3ESetMute%3C/name%3E"
            f"%3Cp%20type=%22str%22%20name=%22mute%22%20val=%22{mute_val}%22/%3E"
        )
        await self._fetch_xml(command)
        self._attr_is_volume_muted = mute

    async def async_select_source(self, source: str) -> None:
        """Change the input source of the soundbar."""
        if source not in self._source_list:
            _LOGGER.error("Unknown source: %s", source)
            return
        # Command: <name>SetFunc</name><p type="str" name="function" val="{source}"/>
        command = (
            f"%3Cname%3ESetFunc%3C/name%3E"
            f"%3Cp%20type=%22str%22%20name=%22function%22%20val=%22{source}%22/%3E"
        )
        await self._fetch_xml(command)
        self._attr_source = source

async def async_setup_platform(
    hass: HomeAssistant,
    config: dict,
    async_add_entities: AddEntitiesCallback,
    discovery_info=None
) -> None:
    """Set up the Samsung Soundbar platform."""
    session = hass.helpers.aiohttp_client.async_get_clientsession(hass)
    async_add_entities([SamsungSoundbar(config, session)], True)
