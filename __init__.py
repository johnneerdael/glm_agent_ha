"""The Llama Query integration."""
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
from .const import DOMAIN, CONF_API_KEY, CONF_WEATHER_ENTITY
from .agent import LlamaAgent

_LOGGER = logging.getLogger(__name__)

LLAMA_API_URL = "https://api.llama.com/v1/chat/completions"

# Define service schema to accept a custom prompt
SERVICE_SCHEMA = vol.Schema({
    vol.Optional('prompt'): cv.string,
})

@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/chat",
    vol.Required("prompt"): str,
})
@websocket_api.async_response
async def websocket_handle_llama(hass, connection, msg):
    """Handle WebSocket messages for Llama chat."""
    response = await handle_llama_query(ServiceCall(DOMAIN, "query", {"prompt": msg.get("prompt")}))
    connection.send_message(websocket_api.result_message(msg["id"], response))

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Llama Query from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    # Initialize the agent with weather entity
    agent = LlamaAgent(
        hass, 
        entry.data[CONF_API_KEY],
        entry.data.get(CONF_WEATHER_ENTITY)
    )
    hass.data[DOMAIN]["agent"] = agent

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

    async def handle_llama_query(call: ServiceCall):
        """Handle the llama_query service."""
        _LOGGER.info("Running LLaMA query service")
        _LOGGER.debug("Service call data: %s", call.data)
        
        # Get the agent from hass data
        agent = hass.data[DOMAIN].get("agent")
        if not agent:
            _LOGGER.error("Agent not initialized")
            hass.bus.async_fire("llama_query_response", {
                "success": False,
                "error": "Agent not initialized"
            })
            return

        try:
            # Process the query using the agent
            result = await agent.process_query(call.data.get('prompt', "how are you today?"))
            _LOGGER.debug("Agent response: %s", result)
            
            if not result:
                hass.bus.async_fire("llama_query_response", {
                    "success": False,
                    "error": "No response from agent"
                })
                return
            
            # Fire event with the result
            hass.bus.async_fire("llama_query_response", result)
            
        except Exception as e:
            _LOGGER.exception("Error processing query: %s", str(e))
            hass.bus.async_fire("llama_query_response", {
                "success": False,
                "error": f"Error processing query: {str(e)}"
            })

    # Register the service
    hass.services.async_register(
        DOMAIN,
        "query",
        handle_llama_query,
        schema=SERVICE_SCHEMA
    )

    # Register WebSocket command
    websocket_api.async_register_command(hass, websocket_handle_llama)

    return True

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Llama Query component."""
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    try:
        from homeassistant.components.frontend import async_remove_panel
        await async_remove_panel(hass, "llama-chat")
    except Exception as e:
        _LOGGER.debug("Error removing panel: %s", str(e))

    hass.data[DOMAIN].pop(entry.entry_id)
    return True
