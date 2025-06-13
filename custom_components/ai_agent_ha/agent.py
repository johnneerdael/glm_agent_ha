"""
Example config:
ai_agent_ha:
  ai_provider: openai  # or 'llama', 'gemini', 'openrouter', 'anthropic'
  llama_token: "..."
  openai_token: "..."
  gemini_token: "..."
  openrouter_token: "..."
  anthropic_token: "..."
  # Model configuration (optional, defaults will be used if not specified)
  models:
    openai: "gpt-3.5-turbo"  # or "gpt-4", "gpt-4-turbo", etc.
    llama: "Llama-4-Maverick-17B-128E-Instruct-FP8"
    gemini: "gemini-1.5-flash"  # or "gemini-1.5-pro", "gemini-1.0-pro", etc.
    openrouter: "openai/gpt-4o"  # or any model available on OpenRouter
    anthropic: "claude-3-5-sonnet-20241022"  # or "claude-3-opus-20240229", etc.
"""
"""The AI Agent implementation with multiple provider support."""
import logging
import json
import aiohttp
import time
import yaml
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from homeassistant.helpers.storage import Store
from .const import DOMAIN, CONF_WEATHER_ENTITY

_LOGGER = logging.getLogger(__name__)

# === AI Client Abstractions ===
class BaseAIClient:
    async def get_response(self, messages, **kwargs):
        raise NotImplementedError

class LlamaClient(BaseAIClient):
    def __init__(self, token, model="Llama-4-Maverick-17B-128E-Instruct-FP8"):
        self.token = token
        self.model = model
        self.api_url = "https://api.llama.com/v1/chat/completions"
    
    async def get_response(self, messages, **kwargs):
        _LOGGER.debug("Making request to Llama API with model: %s", self.model)
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 2048,
            "temperature": 0.7,
            "top_p": 0.9
        }

        _LOGGER.debug("Llama request payload: %s", json.dumps(payload, indent=2))

        async with aiohttp.ClientSession() as session:
            async with session.post(self.api_url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=300)) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    _LOGGER.error("Llama API error %d: %s", resp.status, error_text)
                    raise Exception(f"Llama API error {resp.status}")
                data = await resp.json()
                # Extract text from Llama response
                completion = data.get('completion_message', {})
                content = completion.get('content', {})
                return content.get('text', str(data))

class OpenAIClient(BaseAIClient):
    def __init__(self, token, model="gpt-3.5-turbo"):
        self.token = token
        self.model = model
        self.api_url = "https://api.openai.com/v1/chat/completions"
    
    async def get_response(self, messages, **kwargs):
        _LOGGER.debug("Making request to OpenAI API with model: %s", self.model)
        
        # Validate token
        if not self.token or not self.token.startswith("sk-"):
            raise Exception("Invalid OpenAI API key format")
            
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 2048,
            "temperature": 0.7,
            "top_p": 0.9
        }
        
        _LOGGER.debug("OpenAI request payload: %s", json.dumps(payload, indent=2))
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.api_url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=300)) as resp:
                response_text = await resp.text()
                _LOGGER.debug("OpenAI API response status: %d", resp.status)
                _LOGGER.debug("OpenAI API response: %s", response_text[:500])
                
                if resp.status != 200:
                    _LOGGER.error("OpenAI API error %d: %s", resp.status, response_text)
                    raise Exception(f"OpenAI API error {resp.status}: {response_text}")
                    
                try:
                    data = json.loads(response_text)
                except json.JSONDecodeError as e:
                    _LOGGER.error("Failed to parse OpenAI response as JSON: %s", str(e))
                    raise Exception(f"Invalid JSON response from OpenAI: {response_text[:200]}")
                
                # Extract text from OpenAI response
                choices = data.get('choices', [])
                if choices and 'message' in choices[0]:
                    content = choices[0]['message'].get('content', '')
                    if not content:
                        _LOGGER.warning("OpenAI returned empty content in message")
                        _LOGGER.debug("Full OpenAI response: %s", json.dumps(data, indent=2))
                    return content
                else:
                    _LOGGER.warning("OpenAI response missing expected structure")
                    _LOGGER.debug("Full OpenAI response: %s", json.dumps(data, indent=2))
                    return str(data)

class GeminiClient(BaseAIClient):
    def __init__(self, token, model="gemini-1.5-flash"):
        self.token = token
        self.model = model
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    
    async def get_response(self, messages, **kwargs):
        _LOGGER.debug("Making request to Gemini API with model: %s", self.model)
        
        # Validate token
        if not self.token:
            raise Exception("Missing Gemini API key")
        
        headers = {
            "Content-Type": "application/json"
        }
        
        # Convert OpenAI-style messages to Gemini format
        gemini_contents = []
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            
            if role == "system":
                # Gemini doesn't have a system role, so we prepend it to the first user message
                if not gemini_contents:
                    gemini_contents.append({
                        "role": "user",
                        "parts": [{"text": f"System: {content}"}]
                    })
                else:
                    # Add system message as user message
                    gemini_contents.append({
                        "role": "user", 
                        "parts": [{"text": f"System: {content}"}]
                    })
            elif role == "user":
                gemini_contents.append({
                    "role": "user",
                    "parts": [{"text": content}]
                })
            elif role == "assistant":
                gemini_contents.append({
                    "role": "model",
                    "parts": [{"text": content}]
                })
        
        payload = {
            "contents": gemini_contents,
            "generationConfig": {
                "temperature": 0.7,
                "topP": 0.9,
                "maxOutputTokens": 2048
            }
        }
        
        # Add API key as query parameter
        url_with_key = f"{self.api_url}?key={self.token}"
        
        _LOGGER.debug("Gemini request payload: %s", json.dumps(payload, indent=2))
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url_with_key, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=300)) as resp:
                response_text = await resp.text()
                _LOGGER.debug("Gemini API response status: %d", resp.status)
                _LOGGER.debug("Gemini API response: %s", response_text[:500])
                
                if resp.status != 200:
                    _LOGGER.error("Gemini API error %d: %s", resp.status, response_text)
                    raise Exception(f"Gemini API error {resp.status}: {response_text}")
                    
                try:
                    data = json.loads(response_text)
                except json.JSONDecodeError as e:
                    _LOGGER.error("Failed to parse Gemini response as JSON: %s", str(e))
                    raise Exception(f"Invalid JSON response from Gemini: {response_text[:200]}")
                
                # Extract text from Gemini response
                candidates = data.get('candidates', [])
                if candidates and 'content' in candidates[0]:
                    parts = candidates[0]['content'].get('parts', [])
                    if parts:
                        content = parts[0].get('text', '')
                        if not content:
                            _LOGGER.warning("Gemini returned empty text content")
                            _LOGGER.debug("Full Gemini response: %s", json.dumps(data, indent=2))
                        return content
                    else:
                        _LOGGER.warning("Gemini response missing parts")
                        _LOGGER.debug("Full Gemini response: %s", json.dumps(data, indent=2))
                else:
                    _LOGGER.warning("Gemini response missing expected structure")
                    _LOGGER.debug("Full Gemini response: %s", json.dumps(data, indent=2))
                return str(data)

class AnthropicClient(BaseAIClient):
    def __init__(self, token, model="claude-3-5-sonnet-20241022"):
        self.token = token
        self.model = model
        self.api_url = "https://api.anthropic.com/v1/messages"
    
    async def get_response(self, messages, **kwargs):
        _LOGGER.debug("Making request to Anthropic API with model: %s", self.model)
        headers = {
            "x-api-key": self.token,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        # Convert OpenAI-style messages to Anthropic format
        system_message = None
        anthropic_messages = []
        
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            
            if role == "system":
                # Anthropic uses a separate system parameter
                system_message = content
            elif role == "user":
                anthropic_messages.append({
                    "role": "user",
                    "content": content
                })
            elif role == "assistant":
                anthropic_messages.append({
                    "role": "assistant", 
                    "content": content
                })
        
        payload = {
            "model": self.model,
            "max_tokens": 2048,
            "temperature": 0.7,
            "messages": anthropic_messages
        }
        
        # Add system message if present
        if system_message:
            payload["system"] = system_message
        
        _LOGGER.debug("Anthropic request payload: %s", json.dumps(payload, indent=2))
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.api_url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    _LOGGER.error("Anthropic API error %d: %s", resp.status, error_text)
                    raise Exception(f"Anthropic API error {resp.status}")
                data = await resp.json()
                # Extract text from Anthropic response
                content_blocks = data.get('content', [])
                if content_blocks and isinstance(content_blocks, list):
                    # Get the text from the first content block
                    for block in content_blocks:
                        if block.get('type') == 'text':
                            return block.get('text', str(data))
                return str(data)

class OpenRouterClient(BaseAIClient):
    def __init__(self, token, model="openai/gpt-4o"):
        self.token = token
        self.model = model
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
    
    async def get_response(self, messages, **kwargs):
        _LOGGER.debug("Making request to OpenRouter API with model: %s", self.model)
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://home-assistant.io",  # Optional for OpenRouter rankings
            "X-Title": "Home Assistant AI Agent"  # Optional for OpenRouter rankings
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 2048,
            "temperature": 0.7,
            "top_p": 0.9
        }

        _LOGGER.debug("OpenRouter request payload: %s", json.dumps(payload, indent=2))

        async with aiohttp.ClientSession() as session:
            async with session.post(self.api_url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=300)) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    _LOGGER.error("OpenRouter API error %d: %s", resp.status, error_text)
                    raise Exception(f"OpenRouter API error {resp.status}")
                data = await resp.json()
                # Extract text from OpenRouter response (OpenAI-compatible format)
                choices = data.get('choices', [])
                if not choices:
                    _LOGGER.warning("OpenRouter response missing choices")
                    _LOGGER.debug("Full OpenRouter response: %s", json.dumps(data, indent=2))
                    return str(data)
                if choices and 'message' in choices[0]:
                    return choices[0]['message'].get('content', str(data))
                return str(data)

# === Main Agent ===
class AiAgentHaAgent:
    """Agent for handling queries with dynamic data requests and multiple AI providers."""

    SYSTEM_PROMPT = {
        "role": "system",
        "content": (
            "You are an AI assistant integrated with Home Assistant.\n"
            "You can request specific data by using only these commands:\n"
            "- get_entity_state(entity_id): Get state of a specific entity\n"
            "- get_entities_by_domain(domain): Get all entities in a domain\n"
            "- get_calendar_events(entity_id?): Get calendar events\n"
            "- get_automations(): Get all automations\n"
            "- get_weather_data(): Get current weather and forecast data\n"
            "- get_entity_registry(): Get entity registry entries\n"
            "- get_device_registry(): Get device registry entries\n"
            "- get_area_registry(): Get room/area information\n"
            "- get_history(entity_id, hours): Get historical state changes\n"
            "- get_logbook_entries(hours): Get recent events\n"
            "- get_person_data(): Get person tracking information\n"
            "- get_statistics(entity_id): Get sensor statistics\n"
            "- get_scenes(): Get scene configurations\n"
            "- set_entity_state(entity_id, state, attributes?): Set state of an entity (e.g., turn on/off lights, open/close covers)\n"
            "- create_automation(automation): Create a new automation with the provided configuration\n\n"
            "You can also create automations when users ask for them. When you detect that a user wants to create an automation. make sure to request first entities so you know the entities ids to trigger on. pay attention that if you want to set specfic days in the autoamtion you should use those days: ['fri', 'mon', 'sat', 'sun', 'thu', 'tue', 'wed'] \n"
            "respond with a JSON object in this format:\n"
            "{\n"
            "  \"request_type\": \"automation_suggestion\",\n"
            "  \"automation\": {\n"
            "    \"alias\": \"Name of the automation\",\n"
            "    \"description\": \"Description of what the automation does\",\n"
            "    \"trigger\": [...],  // Array of trigger conditions\n"
            "    \"condition\": [...], // Optional array of conditions\n"
            "    \"action\": [...]     // Array of actions to perform\n"
            "  }\n"
            "}\n\n"
            "For all other responses, use this exact JSON format:\n"
            "{\n"
            "  \"request_type\": \"data_request\",\n"
            "  \"request\": \"command_name\",\n"
            "  \"parameters\": {...}\n"
            "}\n\n"
            "When you have all the data you need, respond with this exact JSON format:\n"
            "{\n"
            "  \"request_type\": \"final_response\",\n"
            "  \"response\": \"your answer to the user\"\n"
            "}\n\n"
            "IMPORTANT: You must ALWAYS respond with a valid JSON object. Do not include any text before or after the JSON. use only the commands above.\n"
            "DO NOT include any special characters or formatting in your response."
        )
    }

    def __init__(self, hass: HomeAssistant, config: Dict[str, Any]):
        """Initialize the agent with provider selection."""
        self.hass = hass
        self.config = config
        self.conversation_history = []
        self._cache = {}
        self._cache_timeout = 300  # 5 minutes
        self._max_retries = 3
        self._retry_delay = 1  # seconds
        self._rate_limit = 60  # requests per minute
        self._last_request_time = 0
        self._request_count = 0
        self._request_window_start = time.time()
        
        provider = config.get("ai_provider", "openai")
        models_config = config.get("models", {})
        
        _LOGGER.debug("Initializing AiAgentHaAgent with provider: %s", provider)
        
        # Initialize the appropriate AI client with model selection
        if provider == "openai":
            model = models_config.get("openai", "gpt-3.5-turbo")
            self.ai_client = OpenAIClient(config.get("openai_token"), model)
        elif provider == "gemini":
            model = models_config.get("gemini", "gemini-1.5-flash")
            self.ai_client = GeminiClient(config.get("gemini_token"), model)
        elif provider == "openrouter":
            model = models_config.get("openrouter", "openai/gpt-4o")
            self.ai_client = OpenRouterClient(config.get("openrouter_token"), model)
        elif provider == "anthropic":
            model = models_config.get("anthropic", "claude-3-5-sonnet-20241022")
            self.ai_client = AnthropicClient(config.get("anthropic_token"), model)
        else:  # default to llama if somehow specified
            model = models_config.get("llama", "Llama-4-Maverick-17B-128E-Instruct-FP8")
            self.ai_client = LlamaClient(config.get("llama_token"), model)
        
        _LOGGER.debug("AiAgentHaAgent initialized successfully with provider: %s, model: %s", provider, model)

    def _validate_api_key(self) -> bool:
        """Validate the API key format."""
        provider = self.config.get("ai_provider", "openai")
        
        if provider == "openai":
            token = self.config.get("openai_token")
        elif provider == "gemini":
            token = self.config.get("gemini_token")
        elif provider == "openrouter":
            token = self.config.get("openrouter_token")
        elif provider == "anthropic":
            token = self.config.get("anthropic_token")
        else:
            token = self.config.get("llama_token")
        
        if not token or not isinstance(token, str):
            return False
        # Add more specific validation based on your API key format
        return len(token) >= 32

    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits."""
        current_time = time.time()
        if current_time - self._request_window_start >= 60:
            self._request_count = 0
            self._request_window_start = current_time
        
        if self._request_count >= self._rate_limit:
            return False
        
        self._request_count += 1
        return True

    def _get_cached_data(self, key: str) -> Optional[Any]:
        """Get data from cache if it's still valid."""
        if key in self._cache:
            timestamp, data = self._cache[key]
            if time.time() - timestamp < self._cache_timeout:
                return data
            del self._cache[key]
        return None

    def _set_cached_data(self, key: str, data: Any) -> None:
        """Store data in cache with timestamp."""
        self._cache[key] = (time.time(), data)

    def _sanitize_automation_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize automation configuration to prevent injection attacks."""
        sanitized = {}
        for key, value in config.items():
            if key in ['alias', 'description']:
                # Sanitize strings
                sanitized[key] = str(value).strip()[:100]  # Limit length
            elif key in ['trigger', 'condition', 'action']:
                # Validate arrays
                if isinstance(value, list):
                    sanitized[key] = value
            elif key == 'mode':
                # Validate mode
                if value in ['single', 'restart', 'queued', 'parallel']:
                    sanitized[key] = value
        return sanitized

    async def get_entity_state(self, entity_id: str) -> Dict[str, Any]:
        """Get the state of a specific entity."""
        try:
            _LOGGER.debug("Requesting entity state for: %s", entity_id)
            state = self.hass.states.get(entity_id)
            if not state:
                _LOGGER.warning("Entity not found: %s", entity_id)
                return {"error": f"Entity {entity_id} not found"}
            
            result = {
                "entity_id": state.entity_id,
                "state": state.state,
                "last_changed": state.last_changed.isoformat() if state.last_changed else None,
                "friendly_name": state.attributes.get("friendly_name"),
                "attributes": {k: (v.isoformat() if hasattr(v, 'isoformat') else v) 
                            for k, v in state.attributes.items()}
            }
            _LOGGER.debug("Retrieved entity state: %s", json.dumps(result))
            return result
        except Exception as e:
            _LOGGER.exception("Error getting entity state: %s", str(e))
            return {"error": f"Error getting entity state: {str(e)}"}

    async def get_entities_by_domain(self, domain: str) -> List[Dict[str, Any]]:
        """Get all entities for a specific domain."""
        try:
            _LOGGER.debug("Requesting all entities for domain: %s", domain)
            states = [state for state in self.hass.states.async_all() 
                    if state.entity_id.startswith(f"{domain}.")]
            _LOGGER.debug("Found %d entities in domain %s", len(states), domain)
            return [await self.get_entity_state(state.entity_id) for state in states]
        except Exception as e:
            _LOGGER.exception("Error getting entities by domain: %s", str(e))
            return [{"error": f"Error getting entities for domain {domain}: {str(e)}"}]

    async def get_calendar_events(self, entity_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get calendar events, optionally filtered by entity_id."""
        try:
            if entity_id:
                _LOGGER.debug("Requesting calendar events for specific entity: %s", entity_id)
                return [await self.get_entity_state(entity_id)]
            
            _LOGGER.debug("Requesting all calendar events")
            return await self.get_entities_by_domain("calendar")
        except Exception as e:
            _LOGGER.exception("Error getting calendar events: %s", str(e))
            return [{"error": f"Error getting calendar events: {str(e)}"}]

    async def get_automations(self) -> List[Dict[str, Any]]:
        """Get all automations."""
        try:
            _LOGGER.debug("Requesting all automations")
            return await self.get_entities_by_domain("automation")
        except Exception as e:
            _LOGGER.exception("Error getting automations: %s", str(e))
            return [{"error": f"Error getting automations: {str(e)}"}]

    async def get_entity_registry(self) -> List[Dict]:
        """Get entity registry entries"""
        _LOGGER.debug("Requesting all entity registry entries")
        try:
            from homeassistant.helpers import entity_registry as er
            registry = er.async_get(self.hass)
            if not registry:
                return []
            return [
                {
                    "entity_id": entry.entity_id,
                    "device_id": entry.device_id,
                    "platform": entry.platform,
                    "disabled": entry.disabled,
                    "area_id": entry.area_id,
                    "original_name": entry.original_name,
                    "unique_id": entry.unique_id
                } 
                for entry in registry.entities.values()
            ]
        except Exception as e:
            _LOGGER.exception("Error getting entity registry entries: %s", str(e))
            return [{"error": f"Error getting entity registry entries: {str(e)}"}]

    async def get_device_registry(self) -> List[Dict]:
        """Get device registry entries"""
        _LOGGER.debug("Requesting all device registry entries")
        try:
            from homeassistant.helpers import device_registry as dr
            registry = dr.async_get(self.hass)
            if not registry:
                return []
            return [
                {
                    "id": device.id,
                    "name": device.name,
                    "model": device.model,
                    "manufacturer": device.manufacturer,
                    "sw_version": device.sw_version,
                    "hw_version": device.hw_version,
                    "connections": list(device.connections) if device.connections else [],
                    "identifiers": list(device.identifiers) if device.identifiers else [],
                    "area_id": device.area_id,
                    "disabled": device.disabled_by is not None,
                    "entry_type": device.entry_type.value if device.entry_type else None,
                    "name_by_user": device.name_by_user
                }
                for device in registry.devices.values()
            ]
        except Exception as e:
            _LOGGER.exception("Error getting device registry entries: %s", str(e))
            return [{"error": f"Error getting device registry entries: {str(e)}"}]

    async def get_history(self, entity_id: str, hours: int = 24) -> List[Dict]:
        """Get historical state changes for an entity"""
        _LOGGER.debug("Requesting historical state changes for entity: %s", entity_id)
        try:
            from homeassistant.components import history
            now = dt_util.utcnow()
            start = now - timedelta(hours=hours)
            
            # Get history using the history component
            history_data = await self.hass.async_add_executor_job(
                history.get_significant_states,
                self.hass, start, now, [entity_id]
            )
            
            # Convert to serializable format
            result = []
            for entity_id_key, states in history_data.items():
                for state in states:
                    result.append({
                        "entity_id": state.entity_id,
                        "state": state.state,
                        "last_changed": state.last_changed.isoformat(),
                        "last_updated": state.last_updated.isoformat(),
                        "attributes": dict(state.attributes)
                    })
            return result
        except Exception as e:
            _LOGGER.exception("Error getting history: %s", str(e))
            return [{"error": f"Error getting history: {str(e)}"}]
    
    async def get_logbook_entries(self, hours: int = 24) -> List[Dict]:
        """Get recent logbook entries"""
        _LOGGER.debug("Requesting recent logbook entries")
        try:
            from homeassistant.components import logbook
            now = dt_util.utcnow()
            start = now - timedelta(hours=hours)
            
            # Get logbook entries
            entries = await self.hass.async_add_executor_job(
                logbook.get_events, self.hass, start, now
            )
            
            # Convert to serializable format
            result = []
            for entry in entries:
                result.append({
                    "when": entry.get("when"),
                    "name": entry.get("name"),
                    "message": entry.get("message"),
                    "entity_id": entry.get("entity_id"),
                    "state": entry.get("state"),
                    "domain": entry.get("domain")
                })
            return result
        except Exception as e:
            _LOGGER.exception("Error getting logbook entries: %s", str(e))
            return [{"error": f"Error getting logbook entries: {str(e)}"}]

    async def get_area_registry(self) -> Dict[str, Dict]:
        """Get area registry information"""
        _LOGGER.debug("Get area registry information")
        try:
            from homeassistant.helpers import area_registry as ar
            registry = ar.async_get(self.hass)
            if not registry:
                return {}
            
            result = {}
            for area in registry.areas.values():
                result[area.id] = {
                    "name": area.name,
                    "normalized_name": area.normalized_name,
                    "picture": area.picture,
                    "icon": area.icon,
                    "floor_id": area.floor_id,
                    "labels": list(area.labels) if area.labels else []
                }
            return result
        except Exception as e:
            _LOGGER.exception("Error getting area registry: %s", str(e))
            return {"error": f"Error getting area registry: {str(e)}"}
        
    async def get_person_data(self) -> List[Dict]:
        """Get person tracking information"""
        _LOGGER.debug("Requesting person tracking information")
        try:
            result = []
            for state in self.hass.states.async_all("person"):
                result.append({
                    "entity_id": state.entity_id,
                    "name": state.attributes.get("friendly_name", state.entity_id),
                    "state": state.state,
                    "latitude": state.attributes.get("latitude"),
                    "longitude": state.attributes.get("longitude"),
                    "source": state.attributes.get("source"),
                    "gps_accuracy": state.attributes.get("gps_accuracy"),
                    "last_changed": state.last_changed.isoformat() if state.last_changed else None
                })
            return result
        except Exception as e:
            _LOGGER.exception("Error getting person tracking information: %s", str(e))
            return [{"error": f"Error getting person tracking information: {str(e)}"}]
    
    async def get_statistics(self, entity_id: str) -> Dict:
        """Get statistics for an entity"""
        _LOGGER.debug("Requesting statistics for entity: %s", entity_id)
        try:
            from homeassistant.components import recorder
            # Check if recorder is available
            if not self.hass.data.get(recorder.DATA_INSTANCE):
                return {"error": "Recorder component is not available"}
                
            # from homeassistant.components.recorder.statistics import get_latest_short_term_statistics
            import homeassistant.components.recorder.statistics as stats_module

            # Get latest statistics
            stats = await self.hass.async_add_executor_job(
                # get_latest_short_term_statistics,
                stats_module.get_last_short_term_statistics,
                self.hass, 1, entity_id, True, set()
            )
            
            if entity_id in stats:
                stat_data = stats[entity_id][0] if stats[entity_id] else {}
                return {
                    "entity_id": entity_id,
                    "start": stat_data.get("start"),
                    "mean": stat_data.get("mean"),
                    "min": stat_data.get("min"),
                    "max": stat_data.get("max"),
                    "last_reset": stat_data.get("last_reset"),
                    "state": stat_data.get("state"),
                    "sum": stat_data.get("sum")
                }
            else:
                return {"error": f"No statistics available for entity {entity_id}"}
        except Exception as e:
            _LOGGER.exception("Error getting statistics: %s", str(e))
            return {"error": f"Error getting statistics: {str(e)}"}
        
    async def get_scenes(self) -> List[Dict]:
        """Get scene configurations"""
        _LOGGER.debug("Requesting scene configurations")
        try:
            result = []
            for state in self.hass.states.async_all("scene"):
                result.append({
                    "entity_id": state.entity_id,
                    "name": state.attributes.get("friendly_name", state.entity_id),
                    "last_activated": state.attributes.get("last_activated"),
                    "icon": state.attributes.get("icon"),
                    "last_changed": state.last_changed.isoformat() if state.last_changed else None
                })
            return result
        except Exception as e:
            _LOGGER.exception("Error getting scene configurations: %s", str(e))
            return [{"error": f"Error getting scene configurations: {str(e)}"}]
        
    async def get_weather_data(self) -> Dict[str, Any]:
        """Get weather data from any available weather entity in the system."""
        try:
            # Find all weather entities
            weather_entities = [
                state for state in self.hass.states.async_all()
                if state.domain == "weather"
            ]
            
            if not weather_entities:
                return {
                    "error": "No weather entities found in the system. Please add a weather integration."
                }
            
            # Use the first available weather entity
            state = weather_entities[0]
            _LOGGER.debug("Using weather entity: %s", state.entity_id)
            
            # Get all available attributes
            all_attributes = state.attributes
            _LOGGER.debug("Available weather attributes: %s", json.dumps(all_attributes))
            
            # Get forecast data
            forecast = all_attributes.get("forecast", [])
            
            # Process forecast data
            processed_forecast = []
            for day in forecast:
                forecast_entry = {
                    "datetime": day.get("datetime"),
                    "temperature": day.get("temperature"),
                    "condition": day.get("condition"),
                    "precipitation": day.get("precipitation"),
                    "precipitation_probability": day.get("precipitation_probability"),
                    "humidity": day.get("humidity"),
                    "wind_speed": day.get("wind_speed"),
                    "wind_bearing": day.get("wind_bearing")
                }
                # Only add entries that have at least some data
                if any(v is not None for v in forecast_entry.values()):
                    processed_forecast.append(forecast_entry)
            
            # Get current weather data
            current = {
                "entity_id": state.entity_id,
                "temperature": all_attributes.get("temperature"),
                "humidity": all_attributes.get("humidity"),
                "pressure": all_attributes.get("pressure"),
                "wind_speed": all_attributes.get("wind_speed"),
                "wind_bearing": all_attributes.get("wind_bearing"),
                "condition": state.state,
                "forecast_available": len(processed_forecast) > 0
            }
            
            # Log the processed data for debugging
            _LOGGER.debug("Processed weather data: %s", json.dumps({
                "current": current,
                "forecast_count": len(processed_forecast)
            }))
            
            return {
                "current": current,
                "forecast": processed_forecast
            }
        except Exception as e:
            _LOGGER.exception("Error getting weather data: %s", str(e))
            return {
                "error": f"Error getting weather data: {str(e)}"
            }

    async def create_automation(self, automation_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new automation with validation and sanitization."""
        try:
            _LOGGER.debug("Creating automation with config: %s", json.dumps(automation_config))
            
            # Validate required fields
            if not all(key in automation_config for key in ['alias', 'trigger', 'action']):
                return {
                    "error": "Missing required fields in automation configuration"
                }
            
            # Sanitize configuration
            sanitized_config = self._sanitize_automation_config(automation_config)
            
            # Generate a unique ID for the automation
            automation_id = f"ai_agent_auto_{int(time.time() * 1000)}"
            
            # Create the automation entry
            automation_entry = {
                'id': automation_id,
                'alias': sanitized_config['alias'],
                'description': sanitized_config.get('description', ''),
                'trigger': sanitized_config['trigger'],
                'condition': sanitized_config.get('condition', []),
                'action': sanitized_config['action'],
                'mode': sanitized_config.get('mode', 'single')
            }
            
            # Read current automations.yaml using async executor
            automations_path = self.hass.config.path('automations.yaml')
            try:
                current_automations = await self.hass.async_add_executor_job(
                    lambda: yaml.safe_load(open(automations_path, 'r')) or []
                )
            except FileNotFoundError:
                current_automations = []
            
            # Check for duplicate automation names
            if any(auto.get('alias') == automation_entry['alias'] for auto in current_automations):
                return {
                    "error": f"An automation with the name '{automation_entry['alias']}' already exists"
                }
            
            # Append new automation
            current_automations.append(automation_entry)
            
            # Write back to file using async executor
            await self.hass.async_add_executor_job(
                lambda: yaml.dump(current_automations, open(automations_path, 'w'), default_flow_style=False)
            )
            
            # Reload automations
            await self.hass.services.async_call('automation', 'reload')
            
            # Clear automation-related caches
            self._cache.clear()
            
            return {
                "success": True,
                "message": f"Automation '{automation_entry['alias']}' created successfully"
            }
            
        except Exception as e:
            _LOGGER.exception("Error creating automation: %s", str(e))
            return {
                "error": f"Error creating automation: {str(e)}"
            }

    async def process_query(self, user_query: str, provider: str = None) -> Dict[str, Any]:
        """Process a user query with input validation and rate limiting."""
        try:
            if not user_query or not isinstance(user_query, str):
                return {"success": False, "error": "Invalid query format"}

            # Get the correct configuration for the requested provider
            if provider and provider in self.hass.data[DOMAIN]["configs"]:
                config = self.hass.data[DOMAIN]["configs"][provider]
            else:
                config = self.config

            _LOGGER.debug(f"Processing query with provider: {provider}")
            _LOGGER.debug(f"Using config: {json.dumps(config, default=str)}")

            selected_provider = provider or config.get("ai_provider", "llama")
            models_config = config.get("models", {})

            provider_config = {
                "openai": {
                    "token_key": "openai_token",
                    "model": models_config.get("openai", "gpt-3.5-turbo"),
                    "client_class": OpenAIClient
                },
                "gemini": {
                    "token_key": "gemini_token",
                    "model": models_config.get("gemini", "gemini-1.5-flash"),
                    "client_class": GeminiClient
                },
                "openrouter": {
                    "token_key": "openrouter_token",
                    "model": models_config.get("openrouter", "openai/gpt-4o"),
                    "client_class": OpenRouterClient
                },
                "llama": {
                    "token_key": "llama_token",
                    "model": models_config.get("llama", "Llama-4-Maverick-17B-128E-Instruct-FP8"),
                    "client_class": LlamaClient
                },
                "anthropic": {
                    "token_key": "anthropic_token",
                    "model": models_config.get("anthropic", "claude-3-5-sonnet-20241022"),
                    "client_class": AnthropicClient
                },
            }

            # Validate provider and get configuration
            if selected_provider not in provider_config:
                _LOGGER.warning(f"Invalid provider {selected_provider}, falling back to llama")
                selected_provider = "llama"

            provider_settings = provider_config[selected_provider]
            token = self.config.get(provider_settings["token_key"])

            # Validate token
            if not token:
                error_msg = f"No token configured for provider {selected_provider}"
                _LOGGER.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg
                }

            # Initialize client
            try:
                self.ai_client = provider_settings["client_class"](
                    token=token,
                    model=provider_settings["model"]
                )
                _LOGGER.debug(f"Initialized {selected_provider} client with model {provider_settings['model']}")
            except Exception as e:
                error_msg = f"Error initializing {selected_provider} client: {str(e)}"
                _LOGGER.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg
                }

            # Process the query with rate limiting and retries
            if not self._check_rate_limit():
                return {
                    "success": False,
                    "error": "Rate limit exceeded. Please wait before trying again."
                }

            # Sanitize user input
            user_query = user_query.strip()[:1000]  # Limit length and trim whitespace
            
            _LOGGER.debug("Processing new query: %s", user_query)
            
            # Check cache for identical query
            cache_key = f"query_{hash(user_query)}"
            cached_result = self._get_cached_data(cache_key)
            if cached_result:
                return cached_result

            # Add system message to conversation if it's the first message
            if not self.conversation_history:
                _LOGGER.debug("Adding system message to new conversation")
                self.conversation_history.append(self.SYSTEM_PROMPT)

            # Add user query to conversation
            self.conversation_history.append({
                "role": "user",
                "content": user_query
            })
            _LOGGER.debug("Added user query to conversation history")

            max_iterations = 5  # Prevent infinite loops
            iteration = 0

            while iteration < max_iterations:
                iteration += 1
                _LOGGER.debug(f"Processing iteration {iteration} of {max_iterations}")
                
                try:
                    # Get AI response
                    _LOGGER.debug("Requesting response from AI provider")
                    response = await self._get_ai_response()
                    _LOGGER.debug("Received response from AI provider: %s", response)
                    
                    try:
                        # Try to parse the response as JSON
                        # First, try to extract JSON from response if it contains extra text
                        response_clean = response.strip()
                        
                        # Look for JSON patterns (starting with { and ending with })
                        json_start = response_clean.find('{')
                        json_end = response_clean.rfind('}')
                        
                        if json_start != -1 and json_end != -1 and json_end > json_start:
                            json_part = response_clean[json_start:json_end + 1]
                            response_data = json.loads(json_part)
                        else:
                            # If no clear JSON pattern, try to parse the whole response
                            response_data = json.loads(response_clean)
                            
                        _LOGGER.debug("Parsed response data: %s", json.dumps(response_data))
                        
                        if response_data.get("request_type") == "data_request":
                            # Handle data request
                            request_type = response_data.get("request")
                            parameters = response_data.get("parameters", {})
                            _LOGGER.debug("Processing data request: %s with parameters: %s", 
                                        request_type, json.dumps(parameters))
                            
                            # Add AI's response to conversation history
                            self.conversation_history.append({
                                "role": "assistant",
                                "content": json.dumps(response_data)  # Store clean JSON
                            })
                            
                            # Get requested data
                            if request_type == "get_entity_state":
                                data = await self.get_entity_state(parameters.get("entity_id"))
                            elif request_type == "get_entities_by_domain":
                                data = await self.get_entities_by_domain(parameters.get("domain"))
                            elif request_type == "get_calendar_events":
                                data = await self.get_calendar_events(parameters.get("entity_id"))
                            elif request_type == "get_automations":
                                data = await self.get_automations()
                            elif request_type == "get_entity_registry":
                                data = await self.get_entity_registry()
                            elif request_type == "get_device_registry":
                                data = await self.get_device_registry()
                            elif request_type == "get_weather_data":
                                data = await self.get_weather_data()
                            elif request_type == "get_area_registry":
                                data = await self.get_area_registry()
                            elif request_type == "get_history":
                                data = await self.get_history(
                                    parameters.get("entity_id"),
                                    parameters.get("hours", 24)
                                )
                            elif request_type == "get_logbook_entries":
                                data = await self.get_logbook_entries(
                                    parameters.get("hours", 24)
                                )
                            elif request_type == "get_person_data":
                                data = await self.get_person_data()
                            elif request_type == "get_statistics":
                                data = await self.get_statistics(
                                    parameters.get("entity_id")
                                )
                            elif request_type == "get_scenes":
                                data = await self.get_scenes()
                            elif request_type == "set_entity_state":
                                data = await self.set_entity_state(
                                    parameters.get("entity_id"),
                                    parameters.get("state"),
                                    parameters.get("attributes")
                                )
                            elif request_type == "create_automation":
                                data = await self.create_automation(
                                    parameters.get("automation")
                                )
                            else:
                                data = {"error": f"Unknown request type: {request_type}"}
                                _LOGGER.warning("Unknown request type: %s", request_type)
                            
                            # Check if any data request resulted in an error
                            if isinstance(data, dict) and "error" in data:
                                return {
                                    "success": False,
                                    "error": data["error"]
                                }
                            elif isinstance(data, list) and any("error" in item for item in data if isinstance(item, dict)):
                                errors = [item["error"] for item in data if isinstance(item, dict) and "error" in item]
                                return {
                                    "success": False,
                                    "error": "; ".join(errors)
                                }
                            
                            _LOGGER.debug("Retrieved data for request: %s", json.dumps(data, default=str))
                            
                            # Add data to conversation as a system message
                            self.conversation_history.append({
                                "role": "system",
                                "content": json.dumps({"data": data}, default=str)
                            })
                            continue
                        
                        elif response_data.get("request_type") == "final_response":
                            # Add final response to conversation history
                            self.conversation_history.append({
                                "role": "assistant",
                                "content": json.dumps(response_data)  # Store clean JSON
                            })
                            
                            # Return final response
                            _LOGGER.debug("Received final response: %s", response_data.get("response"))
                            result = {
                                "success": True,
                                "answer": response_data.get("response", "")
                            }
                            self._set_cached_data(cache_key, result)
                            return result
                        elif response_data.get("request_type") == "automation_suggestion":
                            # Add automation suggestion to conversation history
                            self.conversation_history.append({
                                "role": "assistant",
                                "content": json.dumps(response_data)  # Store clean JSON
                            })
                            
                            # Return automation suggestion
                            _LOGGER.debug("Received automation suggestion: %s", json.dumps(response_data.get("automation")))
                            result = {
                                "success": True,
                                "answer": json.dumps(response_data)
                            }
                            self._set_cached_data(cache_key, result)
                            return result
                        else:
                            _LOGGER.warning("Unknown response type: %s", response_data.get("request_type"))
                            return {
                                "success": False,
                                "error": f"Unknown response type: {response_data.get('request_type')}"
                            }
                            
                    except json.JSONDecodeError as e:
                        _LOGGER.warning("Failed to parse response as JSON: %s. Response: %s", str(e), response[:200])
                        # If response is not valid JSON, return it as final response
                        result = {
                            "success": True,
                            "answer": response
                        }
                        self._set_cached_data(cache_key, result)
                        return result
                        
                except Exception as e:
                    _LOGGER.exception("Error processing AI response: %s", str(e))
                    return {
                        "success": False,
                        "error": f"Error processing AI response: {str(e)}"
                    }

            # If we've reached max iterations without a final response
            _LOGGER.warning("Reached maximum iterations without final response")
            result = {
                "success": False,
                "error": "Maximum iterations reached without final response"
            }
            self._set_cached_data(cache_key, result)
            return result

        except Exception as e:
            _LOGGER.exception("Error in process_query: %s", str(e))
            return {
                "success": False,
                "error": f"Error in process_query: {str(e)}"
            }

    async def _get_ai_response(self) -> str:
        """Get response from the selected AI provider with retries and rate limiting."""
        if not self._check_rate_limit():
            raise Exception("Rate limit exceeded. Please try again later.")
        retry_count = 0
        last_error = None
        # Limit conversation history to last 10 messages to prevent token overflow
        recent_messages = self.conversation_history[-10:] if len(self.conversation_history) > 10 else self.conversation_history
        # Ensure system prompt is always the first message
        if not recent_messages or recent_messages[0].get("role") != "system":
            recent_messages = [self.SYSTEM_PROMPT] + recent_messages
            
        _LOGGER.debug("Sending %d messages to AI provider", len(recent_messages))
        _LOGGER.debug("AI provider: %s", self.config.get("ai_provider", "unknown"))
        
        while retry_count < self._max_retries:
            try:
                _LOGGER.debug("Attempt %d/%d: Calling AI client", retry_count + 1, self._max_retries)
                response = await self.ai_client.get_response(recent_messages)
                _LOGGER.debug("AI client returned response of length: %d", len(response or ""))
                _LOGGER.debug("AI response preview: %s", (response or "")[:200])
                
                # Check if response is empty
                if not response or response.strip() == "":
                    _LOGGER.warning("AI client returned empty response on attempt %d", retry_count + 1)
                    if retry_count + 1 >= self._max_retries:
                        raise Exception("AI provider returned empty response after all retries")
                    else:
                        retry_count += 1
                        await asyncio.sleep(self._retry_delay * retry_count)
                        continue
                        
                return response
            except Exception as e:
                _LOGGER.error("AI client error on attempt %d: %s", retry_count + 1, str(e))
                last_error = e
                retry_count += 1
                if retry_count < self._max_retries:
                    await asyncio.sleep(self._retry_delay * retry_count)
                continue
        raise Exception(f"Failed after {retry_count} retries. Last error: {str(last_error)}")

    def clear_conversation_history(self) -> None:
        """Clear the conversation history and cache."""
        self.conversation_history = []
        self._cache.clear()
        _LOGGER.debug("Conversation history and cache cleared")

    async def set_entity_state(self, entity_id: str, state: str, attributes: Dict[str, Any] = None) -> Dict[str, Any]:
        """Set the state of an entity."""
        try:
            _LOGGER.debug("Setting state for entity %s to %s with attributes: %s", 
                        entity_id, state, json.dumps(attributes or {}))
            
            # Validate entity exists
            if not self.hass.states.get(entity_id):
                return {
                    "error": f"Entity {entity_id} not found"
                }
            
            # Call the appropriate service based on the domain
            domain = entity_id.split('.')[0]
            
            if domain == "light":
                service = "turn_on" if state.lower() in ["on", "true", "1"] else "turn_off"
                service_data = {"entity_id": entity_id}
                if attributes and service == "turn_on":
                    service_data.update(attributes)
                await self.hass.services.async_call("light", service, service_data)
            
            elif domain == "switch":
                service = "turn_on" if state.lower() in ["on", "true", "1"] else "turn_off"
                await self.hass.services.async_call("switch", service, {"entity_id": entity_id})
            
            elif domain == "cover":
                if state.lower() in ["open", "up"]:
                    service = "open_cover"
                elif state.lower() in ["close", "down"]:
                    service = "close_cover"
                elif state.lower() == "stop":
                    service = "stop_cover"
                else:
                    return {"error": f"Invalid state {state} for cover entity"}
                await self.hass.services.async_call("cover", service, {"entity_id": entity_id})
            
            elif domain == "climate":
                service_data = {"entity_id": entity_id}
                if state.lower() in ["on", "true", "1"]:
                    service = "turn_on"
                elif state.lower() in ["off", "false", "0"]:
                    service = "turn_off"
                elif state.lower() in ["heat", "cool", "dry", "fan_only", "auto"]:
                    service = "set_hvac_mode"
                    service_data["hvac_mode"] = state.lower()
                else:
                    return {"error": f"Invalid state {state} for climate entity"}
                await self.hass.services.async_call("climate", service, service_data)
            
            elif domain == "fan":
                service = "turn_on" if state.lower() in ["on", "true", "1"] else "turn_off"
                service_data = {"entity_id": entity_id}
                if attributes and service == "turn_on":
                    service_data.update(attributes)
                await self.hass.services.async_call("fan", service, service_data)
            
            else:
                # For other domains, try to set the state directly
                await self.hass.states.async_set(entity_id, state, attributes or {})
            
            # Get the new state to confirm the change
            new_state = self.hass.states.get(entity_id)
            return {
                "success": True,
                "entity_id": entity_id,
                "new_state": new_state.state,
                "new_attributes": new_state.attributes
            }
            
        except Exception as e:
            _LOGGER.exception("Error setting entity state: %s", str(e))
            return {
                "error": f"Error setting entity state: {str(e)}"
            }

    async def save_user_prompt_history(self, user_id: str, history: List[str]) -> Dict[str, Any]:
        """Save user's prompt history to HA storage."""
        try:
            store = Store(self.hass, 1, f"ai_agent_ha_history_{user_id}")
            await store.async_save({"history": history})
            return {"success": True}
        except Exception as e:
            _LOGGER.exception("Error saving prompt history: %s", str(e))
            return {"error": f"Error saving prompt history: {str(e)}"}

    async def load_user_prompt_history(self, user_id: str) -> Dict[str, Any]:
        """Load user's prompt history from HA storage."""
        try:
            store = Store(self.hass, 1, f"ai_agent_ha_history_{user_id}")
            data = await store.async_load()
            history = data.get("history", []) if data else []
            return {"success": True, "history": history}
        except Exception as e:
            _LOGGER.exception("Error loading prompt history: %s", str(e))
            return {"error": f"Error loading prompt history: {str(e)}", "history": []}