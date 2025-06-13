"""The AI Agent HA integration."""
from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.components.frontend import async_register_built_in_panel
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .agent import AiAgentHaAgent
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

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
        # Convert ConfigEntry to dict and ensure all required keys exist
        config_data = dict(entry.data)
        
        if DOMAIN not in hass.data:
            hass.data[DOMAIN] = {
                "agents": {},
                "configs": {}
            }

        provider = config_data["ai_provider"]
        
        # Store config for this provider
        hass.data[DOMAIN]["configs"][provider] = config_data
        
        # Create agent for this provider
        hass.data[DOMAIN]["agents"][provider] = AiAgentHaAgent(hass, config_data)
        
        _LOGGER.debug(f"Added configuration for provider {provider}")
        
    except Exception as err:
        raise ConfigEntryNotReady(f"Error setting up AI Agent HA: {err}")

    # Modify the query service handler to use the correct provider
    async def async_handle_query(call):
        """Handle the query service call."""
        provider = call.data.get("provider")
        if provider not in hass.data[DOMAIN]["agents"]:
            provider = next(iter(hass.data[DOMAIN]["agents"].keys()))
        
        agent = hass.data[DOMAIN]["agents"][provider]
        result = await agent.process_query(
            call.data.get("prompt", ""),
            provider=provider
        )
        hass.bus.async_fire("ai_agent_ha_response", result)

    async def async_handle_create_automation(call):
        """Handle the create_automation service call."""
        agent = hass.data[DOMAIN]["agents"][call.data.get("provider")]
        result = await agent.create_automation(call.data.get("automation", {}))
        return result

    # Register services
    hass.services.async_register(DOMAIN, "query", async_handle_query)
    hass.services.async_register(DOMAIN, "create_automation", async_handle_create_automation)

    # Register static path for frontend
    await hass.http.async_register_static_paths([
        StaticPathConfig(
            "/frontend/ai_agent_ha",
            hass.config.path("custom_components/ai_agent_ha/frontend"),
            False
        )
    ])

    # Panel registration with proper error handling
    panel_name = "ai_agent_ha"
    try:
        if await _panel_exists(hass, panel_name):
            _LOGGER.debug("AI Agent HA panel already exists, skipping registration")
            return True
        
        _LOGGER.debug("Registering AI Agent HA panel")
        async_register_built_in_panel(
            hass,
            component_name="custom",
            sidebar_title="AI Agent HA",
            sidebar_icon="mdi:robot",
            frontend_url_path=panel_name,
            require_admin=False,
            config={
                "_panel_custom": {
                    "name": "ai_agent_ha-panel",
                    "module_url": "/frontend/ai_agent_ha/ai_agent_ha-panel.js",
                    "embed_iframe": False,
                }
            }
        )
        _LOGGER.debug("AI Agent HA panel registered successfully")
    except Exception as e:
        _LOGGER.warning("Panel registration error: %s", str(e))

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if await _panel_exists(hass, "ai_agent_ha"):
        try:
            from homeassistant.components.frontend import async_remove_panel
            await async_remove_panel(hass, "ai_agent_ha")
            _LOGGER.debug("AI Agent HA panel removed successfully")
        except Exception as e:
            _LOGGER.debug("Error removing panel: %s", str(e))

    # Remove services
    hass.services.async_remove(DOMAIN, "query")
    hass.services.async_remove(DOMAIN, "create_automation")
    
    # Remove data
    if DOMAIN in hass.data:
        hass.data.pop(DOMAIN)
    
    return True

async def _panel_exists(hass: HomeAssistant, panel_name: str) -> bool:
    """Check if a panel already exists."""
    try:
        return (
            hasattr(hass.data, "frontend_panels") 
            and panel_name in hass.data.get("frontend_panels", {})
        )
    except Exception as e:
        _LOGGER.debug("Error checking panel existence: %s", str(e))
        return False
