"""The Llama Query integration."""
from __future__ import annotations

import logging
import json
import aiohttp
import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util
from homeassistant.components import websocket_api
from homeassistant.components.frontend import async_register_built_in_panel
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.helpers.typing import ConfigType
from homeassistant.exceptions import ConfigEntryNotReady
from .const import DOMAIN, CONF_API_KEY, CONF_WEATHER_ENTITY
from .agent import LlamaAgent

_LOGGER = logging.getLogger(__name__)

# Define service schema to accept a custom prompt
SERVICE_SCHEMA = vol.Schema({
    vol.Optional('prompt'): cv.string,
})

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Llama Query component."""
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Llama Query from a config entry."""
    try:
        hass.data[DOMAIN] = {
            "agent": LlamaAgent(
                hass,
                entry.data[CONF_API_KEY],
                entry.data.get(CONF_WEATHER_ENTITY)
            )
        }
    except Exception as err:
        raise ConfigEntryNotReady(f"Error setting up Llama Query: {err}")

    async def async_handle_query(call):
        """Handle the query service call."""
        agent = hass.data[DOMAIN]["agent"]
        result = await agent.process_query(call.data.get("prompt", ""))
        hass.bus.async_fire("llama_query_response", result)

    async def async_handle_create_automation(call):
        """Handle the create_automation service call."""
        agent = hass.data[DOMAIN]["agent"]
        result = await agent.create_automation(call.data.get("automation", {}))
        return result

    # Register services
    hass.services.async_register(DOMAIN, "query", async_handle_query)
    hass.services.async_register(DOMAIN, "create_automation", async_handle_create_automation)

    # Register static path for frontend
    hass.http.register_static_path(
        "/frontend_es5/llama-chat",
        hass.config.path("custom_components/llama_query/frontend"),
        cache_headers=False,
    )

    # Try to unregister existing panel first
    try:
        from homeassistant.components.frontend import async_remove_panel
        await async_remove_panel(hass, "llama-chat")
    except Exception as e:
        _LOGGER.debug("No existing panel to remove: %s", str(e))

    # Register the panel
    try:
        async_register_built_in_panel(
            hass,
            component_name="custom",
            sidebar_title="Llama Chat",
            sidebar_icon="mdi:robot",
            frontend_url_path="llama-chat",
            require_admin=False,
            config={
                "_panel_custom": {
                    "name": "llama-chat-panel",
                    "module_url": "/frontend_es5/llama-chat/llama-chat-panel.js",
                    "embed_iframe": False,
                }
            }
        )
    except ValueError as e:
        _LOGGER.warning("Panel registration error: %s", str(e))
        # If panel already exists, we can continue
        pass

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    try:
        from homeassistant.components.frontend import async_remove_panel
        await async_remove_panel(hass, "llama-chat")
    except Exception as e:
        _LOGGER.debug("Error removing panel: %s", str(e))

    hass.services.async_remove(DOMAIN, "query")
    hass.services.async_remove(DOMAIN, "create_automation")
    hass.data.pop(DOMAIN)
    return True
