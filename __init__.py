from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

DOMAIN = "ipsamsung_soundbar"

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the IP Samsung Soundbar integration from a config entry."""
    # For a simple integration that only has one platform (media_player),
    # you can forward the entry to that platform.
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "media_player")
    )
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an IP Samsung Soundbar config entry."""
    unload_ok = await hass.config_entries.async_forward_entry_unload(entry, "media_player")
    return unload_ok
