from __future__ import annotations

import asyncio
from urllib.parse import quote

import voluptuous as vol
from aiohttp import ClientError

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_NAME, DEFAULT_NAME, DEFAULT_PORT, DOMAIN


def _test_url(host: str, port: int) -> str:
    cmd = quote("<name>GetFeature</name>", safe="")
    return f"http://{host}:{port}/UIC?cmd={cmd}"


class IpSamsungSoundbarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]

            await self.async_set_unique_id(f"{host}:{port}")
            self._abort_if_unique_id_configured()

            session = async_get_clientsession(self.hass)
            try:
                async with asyncio.timeout(4):
                    async with session.get(_test_url(host, port)) as resp:
                        text = await resp.text()
                        if resp.status != 200 or "<response" not in text:
                            errors["base"] = "cannot_connect"
            except (TimeoutError, ClientError):
                errors["base"] = "cannot_connect"

            if not errors:
                return self.async_create_entry(
                    title=user_input.get(CONF_NAME, DEFAULT_NAME),
                    data=user_input,
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
