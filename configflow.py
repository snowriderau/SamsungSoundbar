import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT

DOMAIN = "ipsamsung_soundbar"

class IpsamsungSoundbarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the IP Samsung Soundbar integration."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            # Optionally, perform connectivity tests here.
            return self.async_create_entry(title="IP Samsung Soundbar", data=user_input)

        data_schema = vol.Schema({
            vol.Required(CONF_HOST): str,
            vol.Required(CONF_PORT, default=56001): int,
        })

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )
