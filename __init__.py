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
from .const import DOMAIN, CONF_API_KEY

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

    # Register the panel
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
                "module_url": "/local/llama_query/llama-chat-panel.js",
                "embed_iframe": False,
            }
        }
    )

    async def handle_llama_query(call: ServiceCall):
        """Handle the llama_query service."""
        _LOGGER.info("Running LLaMA query service")

        # Get API key from config entry
        api_key = hass.data[DOMAIN][list(hass.data[DOMAIN].keys())[0]][CONF_API_KEY]

        # Retrieve current time and Home Assistant version
        now = dt_util.now().isoformat()       

        # Get all entity states
        all_states = hass.states.async_all()

        # Helper to shape entity info
        def shape_state(state):
            return {
                "entity_id": state.entity_id,
                "state": state.state,
                "last_changed": state.last_changed.isoformat() if state.last_changed else None,
                "friendly_name": state.attributes.get("friendly_name"),
                "unit": state.attributes.get("unit_measurement"),
                "device_class": state.attributes.get("device_class"),
                "attributes": {k: (v.isoformat() if hasattr(v, 'isoformat') else v) for k, v in state.attributes.items()}
            }

        # Organize entities by domain
        domain_map = {}
        for state in all_states:
            domain = state.entity_id.split('.')[0]
            domain_map.setdefault(domain, []).append(shape_state(state))

        # Build calendar event summary
        calendar_events = []
        for cal in domain_map.get('calendar', []):
            attrs = cal.get('attributes', {})
            calendar_events.append({
                'entity_id': cal['entity_id'],
                'message': attrs.get('message'),
                'start': attrs.get('start_time').isoformat() if hasattr(attrs.get('start_time'), 'isoformat') else attrs.get('start_time'),
                'end': attrs.get('end_time').isoformat() if hasattr(attrs.get('end_time'), 'isoformat') else attrs.get('end_time')
            })

        # Compose context data
        context = {
            'timestamp': now,
            'entity_summary': domain_map,
            'calendar_events': calendar_events
        }

        # Use prompt from service call or default
        user_prompt = call.data.get(
            'prompt',
            "how are you today?"    
        )

        # Prepare payload for LLaMA
        context_json = json.dumps(context, indent=2, default=str)
        _LOGGER.debug(f"Context: {context_json}")
        payload = {
            "model": "Llama-4-Maverick-17B-128E-Instruct-FP8",
            "messages": [
                {"role": "system", "content": "You are an AI assistant integrated with Home Assistant. You have direct access to Home Assistant's internal state and configuration"},
                {"role": "user", "content": f"Snapshot of my Home Assistant environment:\n{context_json}\n\nQuestion: {user_prompt}"}
            ],
            "max_tokens": 2048
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        response_data = {
            "success": False,
            "answer": "",
            "usage": ""
        }

        # Async HTTP request
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(LLAMA_API_URL, headers=headers, json=payload) as resp:
                    raw = await resp.text()
                    if resp.status != 200:
                        error_msg = f"API error {resp.status}: {raw}"
                        _LOGGER.error(f"LLaMA API error: {error_msg}")
                        response_data["error"] = error_msg
                        hass.bus.async_fire(f"{DOMAIN}_response", response_data)
                        return response_data

                    data = json.loads(raw)
                    completion = data.get('completion_message', {})
                    content = completion.get('content', {})
                    if content.get('type') == 'text':
                        answer = content.get('text', '')
                    else:
                        answer = '<no text returned>'

                    # Log the response
                    _LOGGER.info(f"LLaMA answered: {answer}")
                    usage = data.get('metrics', [])
                    usage_str = ', '.join([f"{m['metric']}={m['value']}" for m in usage])

                    response_data.update({
                        "success": True,
                        "answer": answer,
                        "usage": usage_str
                    })

                    # Fire event with the response
                    hass.bus.async_fire(f"{DOMAIN}_response", response_data)

            except Exception as e:
                error_msg = str(e)
                _LOGGER.exception(f"Exception while querying LLaMA: {error_msg}")
                response_data["error"] = error_msg
                hass.bus.async_fire(f"{DOMAIN}_response", response_data)

        return response_data

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
    # Remove the panel
    if DOMAIN in hass.data:
        hass.data.pop(DOMAIN)
    
    return True
