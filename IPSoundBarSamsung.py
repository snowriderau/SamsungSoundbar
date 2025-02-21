import logging
import asyncio
import aiohttp
import async_timeout
import xml.etree.ElementTree as ET

import voluptuous as vol

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    PLATFORM_SCHEMA,
    MediaPlayerState,
)
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

_LOGGER = logging.getLogger(__name__)
DOMAIN = "ipsamsung_soundbar"

SUPPORT_IP_SAMSUNG = (
    MediaPlayerEntityFeature.VOLUME_SET
    | MediaPlayerEntityFeature.VOLUME_MUTE
    | MediaPlayerEntityFeature.TURN_ON
    | MediaPlayerEntityFeature.TURN_OFF
    | MediaPlayerEntityFeature.VOLUME_STEP
    | MediaPlayerEntityFeature.SELECT_SOURCE
)

class IpsamsungSoundbar(MediaPlayerEntity):
    _attr_supported_features = SUPPORT_IP_SAMSUNG
    _attr_icon = "mdi:soundbar"

    def __init__(self, host: str, port: int, name: str = "IP Samsung Soundbar") -> None:
        self._attr_name = name
        self._host = host
        self._port = port
        self._attr_state = MediaPlayerState.OFF
        self._attr_volume_level = 0.0
        self._attr_is_volume_muted = False
        self._attr_source = None
        self._source_list = ["hdmi1", "hdmi2", "optical", "bluetooth"]
        self._base_url = f"http://{self._host}:{self._port}/UIC?cmd="

    @property
    def source_list(self) -> list[str]:
        return self._source_list

    async def async_update(self) -> None:
        """Retrieve the latest state from the soundbar by polling it."""
        # This is where you'd call your GET commands to update state.
        # For example:
        await self._async_get_volume()
        await self._async_get_mute()
        await self._async_get_func()

    async def _fetch_xml(self, command: str) -> ET.Element | None:
        url = self._base_url + command
        try:
            async with async_timeout.timeout(10):
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        text = await response.text()
                        return ET.fromstring(text)
        except Exception as e:
            _LOGGER.error("Error fetching command %s: %s", command, e)
            return None

    async def _async_get_volume(self) -> None:
        command = "%3Cname%3EGetVolume%3C/name%3E"
        root = await self._fetch_xml(command)
        if root is not None:
            volume_elem = root.find(".//volume")
            if volume_elem is not None and volume_elem.text.isdigit():
                volume = int(volume_elem.text)
                self._attr_volume_level = volume / 100.0
                _LOGGER.debug("Volume updated: %s", volume)

    async def _async_get_mute(self) -> None:
        command = "%3Cname%3EGetMute%3C/name%3E"
        root = await self._fetch_xml(command)
        if root is not None:
            mute_elem = root.find(".//mute")
            if mute_elem is not None:
                self._attr_is_volume_muted = (mute_elem.text.lower() == "on")
                _LOGGER.debug("Mute updated: %s", mute_elem.text)

    async def _async_get_func(self) -> None:
        command = "%3Cname%3EGetFunc%3C/name%3E"
        root = await self._fetch_xml(command)
        if root is not None:
            func_elem = root.find(".//function")
            if func_elem is not None:
                self._attr_source = func_elem.text
                _LOGGER.debug("Source updated: %s", func_elem.text)

async def async_setup_entry(hass: HomeAssistant, config_entry) -> bool:
    """Set up the IP Samsung Soundbar from a config entry."""
    host = config_entry.data.get(CONF_HOST)
    port = config_entry.data.get(CONF_PORT)
    name = config_entry.data.get("name", "IP Samsung Soundbar")

    async def async_create_platform():
        hass.async_create_task(
            hass.helpers.discovery.async_load_platform(
                "media_player",
                DOMAIN,
                {
                    "host": host,
                    "port": port,
                    "name": name,
                },
                config_entry,
            )
        )
    hass.async_create_task(async_create_platform())
    return True
