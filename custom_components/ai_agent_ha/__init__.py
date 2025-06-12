"""The AI Agent HA integration."""
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
from .agent import AiAgentHaAgent
from homeassistant.components.http import StaticPathConfig

_LOGGER = logging.getLogger(__name__)

# Config schema - this integration only supports config entries
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

# Define service schema to accept a custom prompt
SERVICE_SCHEMA = vol.Schema({
    vol.Optional('prompt'): cv.string,
})

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the AI Agent HA component."""
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up AI Agent HA from a config entry."""
    try:
        _LOGGER.debug(f"AI Agent HA config entry data: {entry.data}")
        hass.data[DOMAIN] = {
            "agent": AiAgentHaAgent(
                hass,
                entry.data  # Pass the config entry data dict directly
            )
        }
    except Exception as err:
        raise ConfigEntryNotReady(f"Error setting up AI Agent HA: {err}")

    async def async_handle_query(call):
        """Handle the query service call."""
        agent = hass.data[DOMAIN]["agent"]
        result = await agent.process_query(call.data.get("prompt", ""))
        hass.bus.async_fire("ai_agent_ha_response", result)

    async def async_handle_create_automation(call):
        """Handle the create_automation service call."""
        agent = hass.data[DOMAIN]["agent"]
        result = await agent.create_automation(call.data.get("automation", {}))
        return result

    async def async_handle_save_prompt_history(call):
        """Handle the save_prompt_history service call."""
        agent = hass.data[DOMAIN]["agent"]
        user_id = call.context.user_id if call.context.user_id else "default"
        result = await agent.save_user_prompt_history(
            user_id, 
            call.data.get("history", [])
        )
        return result

    async def async_handle_load_prompt_history(call):
        """Handle the load_prompt_history service call."""
        agent = hass.data[DOMAIN]["agent"]
        user_id = call.context.user_id if call.context.user_id else "default"
        result = await agent.load_user_prompt_history(user_id)
        _LOGGER.debug("Load prompt history result: %s", result)
        return result

    # Register services
    hass.services.async_register(DOMAIN, "query", async_handle_query)
    hass.services.async_register(DOMAIN, "create_automation", async_handle_create_automation)
    hass.services.async_register(DOMAIN, "save_prompt_history", async_handle_save_prompt_history)
    hass.services.async_register(DOMAIN, "load_prompt_history", async_handle_load_prompt_history)

    # Register static path for frontend
    await hass.http.async_register_static_paths([
        StaticPathConfig(
            "/frontend/ai_agent_ha",
            hass.config.path("custom_components/ai_agent_ha/frontend"),
            False
        )
    ])

    # Try to unregister existing panel first
    try:
        from homeassistant.components.frontend import async_remove_panel
        await async_remove_panel(hass, "ai_agent_ha")
    except Exception as e:
        _LOGGER.debug("No existing panel to remove: %s", str(e))

    # Register the panel
    try:
        async_register_built_in_panel(
            hass,
            component_name="custom",
            sidebar_title="AI Agent HA",
            sidebar_icon="mdi:robot",
            frontend_url_path="ai_agent_ha",
            require_admin=False,
            config={
                "_panel_custom": {
                    "name": "ai_agent_ha-panel",
                    "module_url": "/frontend/ai_agent_ha/ai_agent_ha-panel.js",
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
        await async_remove_panel(hass, "ai_agent_ha")
    except Exception as e:
        _LOGGER.debug("Error removing panel: %s", str(e))

    hass.services.async_remove(DOMAIN, "query")
    hass.services.async_remove(DOMAIN, "create_automation")
    hass.services.async_remove(DOMAIN, "save_prompt_history")
    hass.services.async_remove(DOMAIN, "load_prompt_history")
    hass.data.pop(DOMAIN)
    return True
