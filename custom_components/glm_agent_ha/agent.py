"""The AI Agent implementation with multiple provider support.

Example config:
glm_agent_ha:
  ai_provider: openai
  openai_token: "..."  # Z.AI API key for GLM Coding Plan
  # Model configuration (optional, defaults will be used if not specified)
  models:
    openai: "GLM-4.6"  # or "GLM-4.5", "GLM-4.5-air".

"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

import aiohttp
import yaml  # type: ignore[import-untyped]
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    CONF_WEATHER_ENTITY,
    DOMAIN,
    CONF_CACHE_TIMEOUT,
    CONF_ENABLE_AREA_TOPOLOGY,
    CONF_ENABLE_ENTITY_TYPE_CACHE,
    CONF_ENABLE_ENTITY_RELATIONSHIPS,
)
from .context.cache import ContextCacheManager
from .context.area_topology import AreaTopologyService
from .context.entity_relationships import EntityRelationshipService
from .mcp_integration import MCPIntegrationManager

_LOGGER = logging.getLogger(__name__)


# === AI Client Abstractions ===
class BaseAIClient:
    async def get_response(self, messages, **kwargs):
        raise NotImplementedError


class LocalClient(BaseAIClient):
    def __init__(self, url, model=""):
        self.url = url
        self.model = model

    async def get_response(self, messages, **kwargs):
        _LOGGER.debug(
            "Making request to local API with model: '%s' at URL: %s",
            self.model or "[NO MODEL SPECIFIED]",
            self.url,
        )

        if not self.model:
            _LOGGER.warning(
                "No model specified for local API request. Some APIs (like Ollama) require a model name."
            )
        headers = {"Content-Type": "application/json"}

        # Format user prompt from messages
        prompt = ""
        for message in messages:
            role = message.get("role", "")
            content = message.get("content", "")

            # Simple formatting: prefixing each message with its role
            if role == "system":
                prompt += f"System: {content}\n\n"
            elif role == "user":
                prompt += f"User: {content}\n\n"
            elif role == "assistant":
                prompt += f"Assistant: {content}\n\n"

        # Add final prompt prefix for the assistant's response
        prompt += "Assistant: "

        # Build a generic payload that works with most local API servers
        payload = {
            "prompt": prompt,
            "stream": False,  # Disable streaming to get a single complete response
        }

        # Add model if specified
        if self.model:
            payload["model"] = self.model

        _LOGGER.debug("Local API request payload: %s", json.dumps(payload, indent=2))

        # Ollama-specific validation
        if "model" not in payload or not payload["model"]:
            _LOGGER.warning(
                "Missing 'model' field in request to local API. This may cause issues with Ollama."
            )
        elif self.url and "ollama" in self.url.lower():
            _LOGGER.debug(
                "Detected Ollama URL, ensuring model is specified: %s",
                payload.get("model"),
            )

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.url,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=300),
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    _LOGGER.error("Local API error %d: %s", resp.status, error_text)

                    # Provide more specific error messages for common Ollama issues
                    if resp.status == 404:
                        if "model" in payload and payload["model"]:
                            raise Exception(
                                f"Model '{payload['model']}' not found. Please ensure the model is installed in Ollama using: ollama pull {payload['model']}"
                            )
                        else:
                            raise Exception(
                                "Local API endpoint not found. Please check the URL and ensure Ollama is running."
                            )
                    elif resp.status == 400:
                        raise Exception(
                            f"Bad request to local API. Error: {error_text}"
                        )
                    else:
                        raise Exception(f"Local API error {resp.status}: {error_text}")

                try:
                    response_text = await resp.text()
                    _LOGGER.debug(
                        "Local API response (first 200 chars): %s", response_text[:200]
                    )
                    _LOGGER.debug("Local API response status: %d", resp.status)
                    _LOGGER.debug("Local API response headers: %s", dict(resp.headers))

                    # Try to parse as JSON
                    try:
                        data = json.loads(response_text)

                        # Try common response formats
                        # Ollama format - return only the response text
                        if "response" in data:
                            response_content = data["response"]
                            _LOGGER.debug(
                                "Extracted response content: %s",
                                (
                                    response_content[:100]
                                    if response_content
                                    else "[EMPTY]"
                                ),
                            )

                            # Check if response is empty or None
                            if not response_content or response_content.strip() == "":
                                _LOGGER.warning(
                                    "Ollama returned empty response. Full data: %s",
                                    data,
                                )
                                # Check if this is a loading response
                                if data.get("done_reason") == "load":
                                    _LOGGER.warning(
                                        "Ollama is still loading the model. Please wait and try again."
                                    )
                                    return json.dumps(
                                        {
                                            "request_type": "final_response",
                                            "response": "The AI model is still loading. Please wait a moment and try again.",
                                        }
                                    )
                                elif data.get("done") is False:
                                    _LOGGER.warning(
                                        "Ollama response indicates it's not done yet."
                                    )
                                    return json.dumps(
                                        {
                                            "request_type": "final_response",
                                            "response": "The AI is still processing your request. Please try again.",
                                        }
                                    )
                                else:
                                    return json.dumps(
                                        {
                                            "request_type": "final_response",
                                            "response": "The AI returned an empty response. Please try rephrasing your question.",
                                        }
                                    )

                            # Check if the response looks like JSON
                            response_content = response_content.strip()
                            if response_content.startswith(
                                "{"
                            ) and response_content.endswith("}"):
                                try:
                                    # Validate that it's actually JSON and contains valid request_type
                                    parsed_json = json.loads(response_content)
                                    if (
                                        isinstance(parsed_json, dict)
                                        and "request_type" in parsed_json
                                    ):
                                        _LOGGER.debug(
                                            "Local model provided valid JSON response"
                                        )
                                        return response_content
                                    else:
                                        _LOGGER.debug(
                                            "JSON missing request_type, treating as plain text"
                                        )
                                except json.JSONDecodeError:
                                    _LOGGER.debug(
                                        "Invalid JSON from local model, treating as plain text"
                                    )
                                    pass

                            # If it's plain text, wrap it in the expected JSON format
                            wrapped_response = {
                                "request_type": "final_response",
                                "response": response_content,
                            }
                            _LOGGER.debug("Wrapped plain text response in JSON format")
                            return json.dumps(wrapped_response)

                        # OpenAI-like format
                        elif "choices" in data and len(data["choices"]) > 0:
                            choice = data["choices"][0]
                            if "message" in choice and "content" in choice["message"]:
                                content = choice["message"]["content"]
                            elif "text" in choice:
                                content = choice["text"]
                            else:
                                content = str(data)

                            # Check if it's valid JSON with request_type
                            content = content.strip()
                            if content.startswith("{") and content.endswith("}"):
                                try:
                                    parsed_json = json.loads(content)
                                    if (
                                        isinstance(parsed_json, dict)
                                        and "request_type" in parsed_json
                                    ):
                                        _LOGGER.debug(
                                            "Local model provided valid JSON response (OpenAI format)"
                                        )
                                        return content
                                    else:
                                        _LOGGER.debug(
                                            "JSON missing request_type, treating as plain text (OpenAI format)"
                                        )
                                except json.JSONDecodeError:
                                    _LOGGER.debug(
                                        "Invalid JSON from local model, treating as plain text (OpenAI format)"
                                    )
                                    pass

                            # Wrap in expected format if plain text
                            wrapped_response = {
                                "request_type": "final_response",
                                "response": content,
                            }
                            return json.dumps(wrapped_response)

                        # Generic content field
                        elif "content" in data:
                            content = data["content"]
                            content = content.strip()
                            if content.startswith("{") and content.endswith("}"):
                                try:
                                    parsed_json = json.loads(content)
                                    if (
                                        isinstance(parsed_json, dict)
                                        and "request_type" in parsed_json
                                    ):
                                        _LOGGER.debug(
                                            "Local model provided valid JSON response (generic format)"
                                        )
                                        return content
                                    else:
                                        _LOGGER.debug(
                                            "JSON missing request_type, treating as plain text (generic format)"
                                        )
                                except json.JSONDecodeError:
                                    _LOGGER.debug(
                                        "Invalid JSON from local model, treating as plain text (generic format)"
                                    )
                                    pass

                            wrapped_response = {
                                "request_type": "final_response",
                                "response": content,
                            }
                            return json.dumps(wrapped_response)

                        # Handle case where no standard fields are found
                        _LOGGER.warning(
                            "No standard response fields found in local API response. Full response: %s",
                            data,
                        )

                        # Check for Ollama-specific edge cases
                        if data.get("done_reason") == "load":
                            return json.dumps(
                                {
                                    "request_type": "final_response",
                                    "response": "The AI model is still loading. Please wait a moment and try again.",
                                }
                            )
                        elif data.get("done") is False:
                            return json.dumps(
                                {
                                    "request_type": "final_response",
                                    "response": "The AI is still processing your request. Please try again.",
                                }
                            )
                        elif "message" in data:
                            # Some APIs use "message" field
                            message_content = data["message"]
                            if (
                                isinstance(message_content, dict)
                                and "content" in message_content
                            ):
                                content = message_content["content"]
                            else:
                                content = str(message_content)
                            return json.dumps(
                                {"request_type": "final_response", "response": content}
                            )

                        # Return the whole data as string if we can't find a specific field
                        return json.dumps(
                            {
                                "request_type": "final_response",
                                "response": f"Received unexpected response format from local API: {str(data)}",
                            }
                        )

                    except json.JSONDecodeError:
                        # If not JSON, check if it's a JSON response that got corrupted by wrapping
                        response_text = response_text.strip()
                        if response_text.startswith("{") and response_text.endswith(
                            "}"
                        ):
                            try:
                                parsed_json = json.loads(response_text)
                                if (
                                    isinstance(parsed_json, dict)
                                    and "request_type" in parsed_json
                                ):
                                    _LOGGER.debug(
                                        "Local model provided valid JSON response (direct)"
                                    )
                                    return response_text
                            except json.JSONDecodeError:
                                pass

                        # If not valid JSON, wrap the raw text in expected format
                        _LOGGER.debug("Response is not JSON, wrapping plain text")
                        wrapped_response = {
                            "request_type": "final_response",
                            "response": response_text,
                        }
                        return json.dumps(wrapped_response)

                except Exception as e:
                    _LOGGER.error("Failed to parse local API response: %s", str(e))
                    raise Exception(f"Failed to parse local API response: {str(e)}")


class OpenAIClient(BaseAIClient):
    """GLM Coding Plan API client using OpenAI-compatible interface.
    
    This client connects to the GLM Coding Plan endpoint at https://api.z.ai/api/coding/paas/v4
    while maintaining compatibility with the OpenAI client library interface.
    """
    
    def __init__(self, token, model="GLM-4.6"):
        self.token = token
        self.model = model if model else "GLM-4.6"
        self.api_url = "https://api.z.ai/api/coding/paas/v4/chat/completions"

    def _get_token_parameter(self):
        """Determine which token parameter to use based on the model."""
        # Models that require max_completion_tokens instead of max_tokens
        completion_token_models = [
            "glm-4.5",
            "glm-4.6",
            "glm-4.5-air"
        ]

        # Check if the model name contains any of the newer model identifiers
        model_lower = self.model.lower()
        if any(model_id in model_lower for model_id in completion_token_models):
            return "max_completion_tokens"
        return "max_tokens"

    def _is_restricted_model(self):
        """Check if the model has restricted parameters (no temperature, top_p, etc.)."""
        # Models that don't support temperature, top_p and other parameters
        restricted_models = ["o3-mini", "o3", "o1-mini", "o1-preview", "o1", "gpt-5"]

        model_lower = self.model.lower()
        return any(model_id in model_lower for model_id in restricted_models)

    async def get_response(self, messages, response_format=None, **kwargs):
        _LOGGER.debug("Making request to GLM Coding Plan API with model: %s", self.model)

        # Validate token - more flexible for GLM Coding Plan API
        if not self.token:
            raise Exception("API key is required")
        
        # Check for minimum length instead of specific prefix
        if len(self.token) < 10:
            raise Exception("API key appears to be too short")

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

        # Determine which token parameter to use
        token_param = self._get_token_parameter()
        is_restricted = self._is_restricted_model()
        _LOGGER.debug(
            "Using token parameter '%s' for model: %s (restricted: %s)",
            token_param,
            self.model,
            is_restricted,
        )

        # Build payload with model-appropriate parameters
        payload = {"model": self.model, "messages": messages, token_param: 2048}
        if response_format:
            payload["response_format"] = response_format

        # Only add temperature and top_p for models that support them
        if not is_restricted:
            payload.update({"temperature": 0.7, "top_p": 0.9})

        _LOGGER.debug("GLM Coding Plan request payload: %s", json.dumps(payload, indent=2))

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=300),
            ) as resp:
                response_text = await resp.text()
                _LOGGER.debug("GLM Coding Plan API response status: %d", resp.status)
                _LOGGER.debug("GLM Coding Plan API response: %s", response_text[:500])

                if resp.status != 200:
                    _LOGGER.error("GLM Coding Plan API error %d: %s", resp.status, response_text)
                    raise Exception(f"GLM Coding Plan API error {resp.status}: {response_text}")

                try:
                    data = json.loads(response_text)
                except json.JSONDecodeError as e:
                    _LOGGER.error("Failed to parse GLM Coding Plan response as JSON: %s", str(e))
                    raise Exception(
                        f"Invalid JSON response from GLM Coding Plan: {response_text[:200]}"
                    )

                # Extract text from GLM Coding Plan response
                choices = data.get("choices", [])
                if choices and "message" in choices[0]:
                    content = choices[0]["message"].get("content", "")
                    if not content:
                        _LOGGER.warning("GLM Coding Plan returned empty content in message")
                        _LOGGER.debug(
                            "Full GLM Coding Plan response: %s", json.dumps(data, indent=2)
                        )
                    return content
                else:
                    _LOGGER.warning("GLM Coding Plan response missing expected structure")
                    _LOGGER.debug(
                        "Full GLM Coding Plan response: %s", json.dumps(data, indent=2)
                    )
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
            "- get_entities_by_area(area_id): Get all entities in a specific area\n"
            "- get_entities(area_id or area_ids): Get entities by area(s) - supports single area_id or list of area_ids\n"
            "  Use as: get_entities(area_ids=['area1', 'area2']) for multiple areas or get_entities(area_id='single_area')\n"
            "- get_calendar_events(entity_id?): Get calendar events\n"
            "- get_automations(): Get all automations\n"
            "- get_weather_data(): Get current weather and forecast data\n"
            "- get_entity_registry(): Get entity registry entries\n"
            "- get_device_registry(): Get device registry entries\n"
            "- get_area_registry(): Get room/area information\n"
            "- get_entity_types_by_area(area_id): Get entity types grouped by domain for a specific area\n"
            "- get_floor_topology(): Get floor topology information including areas and entities per floor\n"
            "- get_entities_by_category(category): Get entities by category (e.g., 'lighting', 'security', 'climate')\n"
            "- get_related_entities(entity_id): Get entities related to a specific entity\n"
            "- get_history(entity_id, hours): Get historical state changes\n"
            "- get_logbook_entries(hours): Get recent events\n"
            "- get_person_data(): Get person tracking information\n"
            "- get_statistics(entity_id): Get sensor statistics\n"
            "- get_scenes(): Get scene configurations\n"
            "- get_dashboards(): Get list of all dashboards\n"
            "- get_dashboard_config(dashboard_url): Get configuration of a specific dashboard\n"
            "- set_entity_state(entity_id, state, attributes?): Set state of an entity (e.g., turn on/off lights, open/close covers)\n"
            "- call_service(domain, service, target?, service_data?): Call any Home Assistant service directly\n"
            "- create_automation(automation): Create a new automation with the provided configuration\n"
            "- create_dashboard(dashboard_config): Create a new dashboard with the provided configuration\n"
            "- update_dashboard(dashboard_url, dashboard_config): Update an existing dashboard configuration\n"
            "- analyze_image(image_source, prompt?): Analyze an image and provide detailed description\n"
            "- analyze_video(video_source, prompt?): Analyze a video and provide detailed description\n"
            "- web_search(query, count?, search_recency_filter?): Search the web for current information\n\n"
            "You can also create dashboards when users ask for them. When creating dashboards:\n"
            "1. First gather information about available entities, areas, and devices\n"
            "2. Ask follow-up questions if the user's requirements are unclear\n"
            "3. Create a dashboard configuration with appropriate cards and views\n"
            "4. Use common card types like: entities, glance, picture-entity, weather-forecast, thermostat, media-control, etc.\n"
            "5. Organize cards logically by rooms, device types, or functionality\n"
            "6. Include relevant entities based on the user's request\n\n"
            "For Pro/Max plans, you can also analyze images and videos, or search the web:\n"
            "- analyze_image: Provide an image URL or path and optionally a specific prompt for analysis\n"
            "- analyze_video: Provide a video URL or path and optionally a specific prompt for analysis\n"
            "- web_search: Search for current information with optional count and recency filters\n\n"
            "IMPORTANT AREA/FLOOR GUIDANCE:\n"
            "- When users ask for entities from a specific floor, use get_area_registry() first\n"
            "- Areas have both 'area_id' and 'floor_id' - these are different concepts\n"
            "- Filter areas by their floor_id to find all areas on a specific floor\n"
            "- Use get_entities() with area_ids parameter to get entities from multiple areas efficiently\n"
            "- Example: get_entities(area_ids=['area1', 'area2', 'area3']) for multiple areas at once\n"
            "- This is more efficient than calling get_entities_by_area() multiple times\n\n"
            "You can also create automations when users ask for them. When you detect that a user wants to create an automation, make sure to request first entities so you know the entity IDs to trigger on. Pay attention that if you want to set specific days in the automation you should use those days: ['fri', 'mon', 'sat', 'sun', 'thu', 'tue', 'wed']\n"
            "IMPORTANT: Keep your response concise and focused. Do NOT repeat text or add unnecessary explanations.\n"
            "Respond with a JSON object in this EXACT format:\n"
            "{\n"
            '  "request_type": "automation_suggestion",\n'
            '  "message": "I\'ve created an automation that might help you. Would you like me to create it?",\n'
            '  "automation": {\n'
            '    "alias": "Name of the automation",\n'
            '    "description": "Description of what the automation does",\n'
            '    "trigger": [...],  // Array of trigger conditions\n'
            '    "condition": [...], // Optional array of conditions\n'
            '    "action": [...]     // Array of actions to perform\n'
            "  }\n"
            "}\n\n"
            "For dashboard creation requests, use this exact JSON format:\n"
            "{\n"
            '  "request_type": "dashboard_suggestion",\n'
            '  "message": "I\'ve created a dashboard configuration for you. Would you like me to create it?",\n'
            '  "dashboard": {\n'
            '    "title": "Dashboard Title",\n'
            '    "url_path": "dashboard-url-path",\n'
            '    "icon": "mdi:icon-name",\n'
            '    "show_in_sidebar": true,\n'
            '    "views": [{\n'
            '      "title": "View Title",\n'
            '      "cards": [...] // Array of card configurations\n'
            "    }]\n"
            "  }\n"
            "}\n\n"
            "For data requests, use this exact JSON format:\n"
            "{\n"
            '  "request_type": "data_request",\n'
            '  "request": "command_name",\n'
            '  "parameters": {...}\n'
            "}\n"
            'For get_entities with multiple areas: {"request_type": "get_entities", "parameters": {"area_ids": ["area1", "area2"]}}\n'
            'For get_entities with single area: {"request_type": "get_entities", "parameters": {"area_id": "single_area"}}\n\n'
            "For service calls, use this exact JSON format:\n"
            "{\n"
            '  "request_type": "call_service",\n'
            '  "domain": "light",\n'
            '  "service": "turn_on",\n'
            '  "target": {"entity_id": ["entity1", "entity2"]},\n'
            '  "service_data": {"brightness": 255}\n'
            "}\n\n"
            "When you have all the data you need, respond with this exact JSON format:\n"
            "{\n"
            '  "request_type": "final_response",\n'
            '  "response": "your answer to the user"\n'
            "}\n\n"
            "CRITICAL FORMATTING RULES:\n"
            "- You must ALWAYS respond with ONLY a valid JSON object\n"
            "- DO NOT include any text before the JSON\n"
            "- DO NOT include any text after the JSON\n"
            "- DO NOT include explanations or descriptions outside the JSON\n"
            "- Your entire response must be parseable as JSON\n"
            "- Use the 'message' field inside the JSON for user-facing text\n"
            "- NEVER mix regular text with JSON in your response\n\n"
            "WRONG: 'I'll create this for you. {\"request_type\": ...}'\n"
            'CORRECT: \'{"request_type": "dashboard_suggestion", "message": "I\'ll create this for you.", ...}\''
        ),
    }

    SYSTEM_PROMPT_LOCAL = {
        "role": "system",
        "content": (
            "You are an AI assistant integrated with Home Assistant.\n"
            "You can request specific data by using only these commands:\n"
            "- get_entity_state(entity_id): Get state of a specific entity\n"
            "- get_entities_by_domain(domain): Get all entities in a domain\n"
            "- get_entities_by_area(area_id): Get all entities in a specific area\n"
            "- get_entities(area_id or area_ids): Get entities by area(s) - supports single area_id or list of area_ids\n"
            "  Use as: get_entities(area_ids=['area1', 'area2']) for multiple areas or get_entities(area_id='single_area')\n"
            "- get_calendar_events(entity_id?): Get calendar events\n"
            "- get_automations(): Get all automations\n"
            "- get_weather_data(): Get current weather and forecast data\n"
            "- get_entity_registry(): Get entity registry entries\n"
            "- get_device_registry(): Get device registry entries\n"
            "- get_area_registry(): Get room/area information\n"
            "- get_entity_types_by_area(area_id): Get entity types grouped by domain for a specific area\n"
            "- get_floor_topology(): Get floor topology information including areas and entities per floor\n"
            "- get_entities_by_category(category): Get entities by category (e.g., 'lighting', 'security', 'climate')\n"
            "- get_related_entities(entity_id): Get entities related to a specific entity\n"
            "- get_history(entity_id, hours): Get historical state changes\n"
            "- get_logbook_entries(hours): Get recent events\n"
            "- get_person_data(): Get person tracking information\n"
            "- get_statistics(entity_id): Get sensor statistics\n"
            "- get_scenes(): Get scene configurations\n"
            "- get_dashboards(): Get list of all dashboards\n"
            "- get_dashboard_config(dashboard_url): Get configuration of a specific dashboard\n"
            "- set_entity_state(entity_id, state, attributes?): Set state of an entity (e.g., turn on/off lights, open/close covers)\n"
            "- call_service(domain, service, target?, service_data?): Call any Home Assistant service directly\n"
            "- create_automation(automation): Create a new automation with the provided configuration\n"
            "- create_dashboard(dashboard_config): Create a new dashboard with the provided configuration\n"
            "- update_dashboard(dashboard_url, dashboard_config): Update an existing dashboard configuration\n\n"
            "You can also create dashboards when users ask for them. When creating dashboards:\n"
            "1. First gather information about available entities, areas, and devices\n"
            "2. Ask follow-up questions if the user's requirements are unclear\n"
            "3. Create a dashboard configuration with appropriate cards and views\n"
            "4. Use common card types like: entities, glance, picture-entity, weather-forecast, thermostat, media-control, etc.\n"
            "5. Organize cards logically by rooms, device types, or functionality\n"
            "6. Include relevant entities based on the user's request\n\n"
            "IMPORTANT AREA/FLOOR GUIDANCE:\n"
            "- When users ask for entities from a specific floor, use get_area_registry() first\n"
            "- Areas have both 'area_id' and 'floor_id' - these are different concepts\n"
            "- Filter areas by their floor_id to find all areas on a specific floor\n"
            "- Use get_entities() with area_ids parameter to get entities from multiple areas efficiently\n"
            "- Example: get_entities(area_ids=['area1', 'area2', 'area3']) for multiple areas at once\n"
            "- This is more efficient than calling get_entities_by_area() multiple times\n\n"
            "You can also create automations when users ask for them. When you detect that a user wants to create an automation, make sure to request first entities so you know the entity IDs to trigger on. Pay attention that if you want to set specific days in the automation you should use those days: ['fri', 'mon', 'sat', 'sun', 'thu', 'tue', 'wed']\n"
            "IMPORTANT: Keep your response concise and focused. Do NOT repeat text or add unnecessary explanations.\n"
            "Respond with a JSON object in this EXACT format:\n"
            "{\n"
            '  "request_type": "automation_suggestion",\n'
            '  "message": "I\'ve created an automation that might help you. Would you like me to create it?",\n'
            '  "automation": {\n'
            '    "alias": "Name of the automation",\n'
            '    "description": "Description of what the automation does",\n'
            '    "trigger": [...],  // Array of trigger conditions\n'
            '    "condition": [...], // Optional array of conditions\n'
            '    "action": [...]     // Array of actions to perform\n'
            "  }\n"
            "}\n\n"
            "For dashboard creation requests, use this exact JSON format:\n"
            "{\n"
            '  "request_type": "dashboard_suggestion",\n'
            '  "message": "I\'ve created a dashboard configuration for you. Would you like me to create it?",\n'
            '  "dashboard": {\n'
            '    "title": "Dashboard Title",\n'
            '    "url_path": "dashboard-url-path",\n'
            '    "icon": "mdi:icon-name",\n'
            '    "show_in_sidebar": true,\n'
            '    "views": [{\n'
            '      "title": "View Title",\n'
            '      "cards": [...] // Array of card configurations\n'
            "    }]\n"
            "  }\n"
            "}\n\n"
            "For data requests, use this exact JSON format:\n"
            "{\n"
            '  "request_type": "data_request",\n'
            '  "request": "command_name",\n'
            '  "parameters": {...}\n'
            "}\n"
            'For get_entities with multiple areas: {"request_type": "get_entities", "parameters": {"area_ids": ["area1", "area2"]}}\n'
            'For get_entities with single area: {"request_type": "get_entities", "parameters": {"area_id": "single_area"}}\n\n'
            "For service calls, use this exact JSON format:\n"
            "{\n"
            '  "request_type": "call_service",\n'
            '  "domain": "light",\n'
            '  "service": "turn_on",\n'
            '  "target": {"entity_id": ["entity1", "entity2"]},\n'
            '  "service_data": {"brightness": 255}\n'
            "}\n\n"
            "When you have all the data you need, respond with this exact JSON format:\n"
            "{\n"
            '  "request_type": "final_response",\n'
            '  "response": "your answer to the user"\n'
            "}\n\n"
            "CRITICAL FORMATTING RULES:\n"
            "- You must ALWAYS respond with ONLY a valid JSON object\n"
            "- DO NOT include any text before the JSON\n"
            "- DO NOT include any text after the JSON\n"
            "- DO NOT include explanations or descriptions outside the JSON\n"
            "- Your entire response must be parseable as JSON\n"
            "- Use the 'message' field inside the JSON for user-facing text\n"
            "- NEVER mix regular text with JSON in your response\n\n"
            "WRONG: 'I'll create this for you. {\"request_type\": ...}'\n"
            'CORRECT: \'{"request_type": "dashboard_suggestion", "message": "I\'ll create this for you.", ...}\''
        ),
    }

    def __init__(self, hass: HomeAssistant, config: Dict[str, Any]):
        """Initialize the agent with provider selection."""
        self.hass = hass
        self.config = config
        self.conversation_history: List[Dict[str, Any]] = []
        self._cache: Dict[str, Any] = {}
        self.ai_client: BaseAIClient
        self._cache_timeout = config.get(CONF_CACHE_TIMEOUT, 300)  # Configurable cache timeout
        self._max_retries = 10
        self._retry_delay = 1  # seconds
        self._rate_limit = 60  # requests per minute
        self._last_request_time = 0
        self._request_count = 0
        self._request_window_start = time.time()
        
        # Initialize context services with feature flags
        self._context_cache = ContextCacheManager(self.hass, self._cache_timeout)
        self._area_topology = AreaTopologyService(
            hass,
            self._context_cache,
            enabled=config.get(CONF_ENABLE_AREA_TOPOLOGY, True)
        )
        
        self._entity_relationships = EntityRelationshipService(
            hass,
            self._context_cache,
            enabled=config.get(CONF_ENABLE_ENTITY_RELATIONSHIPS, True)
        )
        
        # Feature flags
        self._enable_entity_type_cache = config.get(CONF_ENABLE_ENTITY_TYPE_CACHE, True)

        # Initialize MCP integration for Pro/Max plans
        self.mcp_manager = MCPIntegrationManager(hass, config)
        if self.mcp_manager.is_mcp_available():
            _LOGGER.info("MCP integration available for plan: %s", config.get("plan"))
        else:
            _LOGGER.debug("MCP integration not available for plan: %s", config.get("plan"))

        provider = config.get("ai_provider", "openai")
        models_config = config.get("models", {})

        _LOGGER.debug("Initializing AiAgentHaAgent with provider: %s", provider)
        _LOGGER.debug("Models config loaded: %s", models_config)

        # Set the appropriate system prompt based on provider
        if provider == "local":
            self.system_prompt = self.SYSTEM_PROMPT_LOCAL
            _LOGGER.debug("Using local-optimized system prompt")
        else:
            self.system_prompt = self.SYSTEM_PROMPT
            _LOGGER.debug("Using standard system prompt")

        # Initialize the appropriate AI client with model selection
        if provider == "openai":
            model = models_config.get("openai", "GLM-4.5-air")
            self.ai_client = OpenAIClient(config.get("openai_token"), model)
        else:  # default to llama if somehow specified
            model = models_config.get("openai", "GLM-4.5-air")
            self.ai_client = OpenAIClient(config.get("openai_token"), model)

        _LOGGER.debug(
            "AiAgentHaAgent initialized successfully with provider: %s, model: %s",
            provider,
            model,
        )

    def _validate_api_key(self) -> bool:
        """Validate the API key format."""
        provider = self.config.get("ai_provider", "openai")

        if provider == "openai":
            token = self.config.get("openai_token")

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
        return self._context_cache.get(key)

    def _set_cached_data(self, key: str, data: Any) -> None:
        """Store data in cache with timestamp."""
        self._context_cache.set(key, data)

    def _invalidate_context_caches(self) -> None:
        """Invalidate all context-related caches when registries change."""
        self._context_cache.clear_pattern("area_registry")
        self._context_cache.clear_pattern("device_registry")
        self._context_cache.clear_pattern("entity_registry")
        self._context_cache.clear_pattern("area_topology")
        self._context_cache.clear_pattern("entities_by_area")
        self._context_cache.clear_pattern("entities_by_domain")
        self._context_cache.clear_pattern("entity_relationships")
        _LOGGER.debug("Invalidated context caches due to registry changes")

    def _sanitize_automation_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize automation configuration to prevent injection attacks."""
        sanitized: Dict[str, Any] = {}
        for key, value in config.items():
            if key in ["alias", "description"]:
                # Sanitize strings
                sanitized[key] = str(value).strip()[:100]  # Limit length
            elif key in ["trigger", "condition", "action"]:
                # Validate arrays
                if isinstance(value, list):
                    sanitized[key] = value
            elif key == "mode":
                # Validate mode
                if value in ["single", "restart", "queued", "parallel"]:
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
                "last_changed": (
                    state.last_changed.isoformat() if state.last_changed else None
                ),
                "friendly_name": state.attributes.get("friendly_name"),
                "attributes": {
                    k: (v.isoformat() if hasattr(v, "isoformat") else v)
                    for k, v in state.attributes.items()
                },
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
            states = [
                state
                for state in self.hass.states.async_all()
                if state.entity_id.startswith(f"{domain}.")
            ]
            _LOGGER.debug("Found %d entities in domain %s", len(states), domain)
            return [await self.get_entity_state(state.entity_id) for state in states]
        except Exception as e:
            _LOGGER.exception("Error getting entities by domain: %s", str(e))
            return [{"error": f"Error getting entities for domain {domain}: {str(e)}"}]

    async def get_entities_by_area(self, area_id: str) -> List[Dict[str, Any]]:
        """Get all entities for a specific area with caching and topology integration."""
        try:
            _LOGGER.debug("Requesting all entities for area: %s", area_id)

            # Use area topology service if enabled
            # Use area topology service if enabled
            summaries = await self._area_topology.get_area_entities(area_id)
            
            _LOGGER.debug(
                "Found %d entities in area %s", len(summaries), area_id
            )

            # Get state information for each entity
            result = []
            for summary in summaries:
                state_info = await self.get_entity_state(summary.entity_id)
                if not state_info.get("error"):  # Only include entities that exist
                    result.append(state_info)

            return result

        except Exception as e:
            _LOGGER.exception("Error getting entities by area: %s", str(e))
            return [{"error": f"Error getting entities for area {area_id}: {str(e)}"}]

    async def _get_entities_by_area_manual(self, area_id: str) -> List[str]:
        """Manual fallback method for getting entities by area."""
        # Get entity registry to find entities assigned to the area
        from homeassistant.helpers import device_registry as dr
        from homeassistant.helpers import entity_registry as er

        entity_registry = er.async_get(self.hass)
        device_registry = dr.async_get(self.hass)

        entities_in_area = []

        # Find entities assigned to the area (directly or through their device)
        for entity in entity_registry.entities.values():
            # Check if entity is directly assigned to the area
            if entity.area_id == area_id:
                entities_in_area.append(entity.entity_id)
            # Check if entity's device is assigned to the area
            elif entity.device_id:
                device = device_registry.devices.get(entity.device_id)
                if device and device.area_id == area_id:
                    entities_in_area.append(entity.entity_id)

        return entities_in_area

    async def get_entities(self, area_id=None, area_ids=None) -> List[Dict[str, Any]]:
        """Get entities by area(s) - flexible method that supports single area or multiple areas."""
        try:
            # Handle different parameter formats
            areas_to_process = []

            if area_ids:
                # Multiple areas provided
                if isinstance(area_ids, list):
                    areas_to_process = area_ids
                else:
                    areas_to_process = [area_ids]
            elif area_id:
                # Single area provided
                if isinstance(area_id, list):
                    areas_to_process = area_id
                else:
                    areas_to_process = [area_id]
            else:
                return [{"error": "No area_id or area_ids provided"}]

            _LOGGER.debug("Requesting entities for areas: %s", areas_to_process)

            all_entities = []
            for area in areas_to_process:
                entities_in_area = await self.get_entities_by_area(area)
                all_entities.extend(entities_in_area)

            # Remove duplicates based on entity_id
            seen_entities = set()
            unique_entities = []
            for entity in all_entities:
                if isinstance(entity, dict) and "entity_id" in entity:
                    if entity["entity_id"] not in seen_entities:
                        seen_entities.add(entity["entity_id"])
                        unique_entities.append(entity)
                else:
                    unique_entities.append(entity)  # Keep error messages

            _LOGGER.debug(
                "Found %d unique entities across %d areas",
                len(unique_entities),
                len(areas_to_process),
            )
            return unique_entities

        except Exception as e:
            _LOGGER.exception("Error getting entities: %s", str(e))
            return [{"error": f"Error getting entities: {str(e)}"}]

    async def get_calendar_events(
        self, entity_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get calendar events, optionally filtered by entity_id."""
        try:
            if entity_id:
                _LOGGER.debug(
                    "Requesting calendar events for specific entity: %s", entity_id
                )
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
        """Get entity registry entries with caching"""
        cache_key = "entity_registry"
        cached_data = self._get_cached_data(cache_key)
        if cached_data is not None:
            _LOGGER.debug("Returning cached entity registry data")
            return cached_data

        _LOGGER.debug("Requesting all entity registry entries")
        try:
            from homeassistant.helpers import entity_registry as er

            registry = er.async_get(self.hass)
            if not registry:
                result = []
            else:
                result = [
                    {
                        "entity_id": entry.entity_id,
                        "device_id": entry.device_id,
                        "platform": entry.platform,
                        "disabled": entry.disabled,
                        "area_id": entry.area_id,
                        "original_name": entry.original_name,
                        "unique_id": entry.unique_id,
                    }
                    for entry in registry.entities.values()
                ]
            
            self._set_cached_data(cache_key, result)
            return result
        except Exception as e:
            _LOGGER.exception("Error getting entity registry entries: %s", str(e))
            return [{"error": f"Error getting entity registry entries: {str(e)}"}]

    async def get_device_registry(self) -> List[Dict]:
        """Get device registry entries with caching"""
        cache_key = "device_registry"
        cached_data = self._get_cached_data(cache_key)
        if cached_data is not None:
            _LOGGER.debug("Returning cached device registry data")
            return cached_data

        _LOGGER.debug("Requesting all device registry entries")
        try:
            from homeassistant.helpers import device_registry as dr

            registry = dr.async_get(self.hass)
            if not registry:
                result = []
            else:
                result = [
                    {
                        "id": device.id,
                        "name": device.name,
                        "model": device.model,
                        "manufacturer": device.manufacturer,
                        "sw_version": device.sw_version,
                        "hw_version": device.hw_version,
                        "connections": (
                            list(device.connections) if device.connections else []
                        ),
                        "identifiers": (
                            list(device.identifiers) if device.identifiers else []
                        ),
                        "area_id": device.area_id,
                        "disabled": device.disabled_by is not None,
                        "entry_type": (
                            device.entry_type.value if device.entry_type else None
                        ),
                        "name_by_user": device.name_by_user,
                    }
                    for device in registry.devices.values()
                ]
            
            self._set_cached_data(cache_key, result)
            return result
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
                getattr(history, "get_significant_states"),
                self.hass,
                start,
                now,
                [entity_id],
            )

            # Convert to serializable format
            result = []
            for entity_id_key, states in history_data.items():
                for state in states:
                    result.append(
                        {
                            "entity_id": state.entity_id,
                            "state": state.state,
                            "last_changed": state.last_changed.isoformat(),
                            "last_updated": state.last_updated.isoformat(),
                            "attributes": dict(state.attributes),
                        }
                    )
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
                getattr(logbook, "get_events"), self.hass, start, now
            )

            # Convert to serializable format
            result = []
            for entry in entries:
                result.append(
                    {
                        "when": entry.get("when"),
                        "name": entry.get("name"),
                        "message": entry.get("message"),
                        "entity_id": entry.get("entity_id"),
                        "state": entry.get("state"),
                        "domain": entry.get("domain"),
                    }
                )
            return result
        except Exception as e:
            _LOGGER.exception("Error getting logbook entries: %s", str(e))
            return [{"error": f"Error getting logbook entries: {str(e)}"}]

    async def get_area_registry(self) -> Dict[str, Any]:
        """Get area registry information with caching and topology integration"""
        cache_key = "area_registry"
        cached_data = self._get_cached_data(cache_key)
        if cached_data is not None:
            _LOGGER.debug("Returning cached area registry data")
            return cached_data

        _LOGGER.debug("Get area registry information")
        try:
            from homeassistant.helpers import area_registry as ar

            registry = ar.async_get(self.hass)
            if not registry:
                result = {}
            else:
                result = {}
                for area in registry.areas.values():
                    result[area.id] = {
                        "name": area.name,
                        "normalized_name": area.normalized_name,
                        "picture": area.picture,
                        "icon": area.icon,
                        "floor_id": area.floor_id,
                        "labels": list(area.labels) if area.labels else [],
                    }
            
            self._set_cached_data(cache_key, result)
            
            # Invalidate topology cache since area registry has been updated
            if self._area_topology.enabled:
                self._area_topology.invalidate_cache()
            
            if self._entity_relationships.enabled:
                await self._entity_relationships.build_relationship_maps()

            return result
        except Exception as e:
            _LOGGER.exception("Error getting area registry: %s", str(e))
            return {"error": f"Error getting area registry: {str(e)}"}

    async def get_entity_types_by_area(self, area_id: str) -> Dict[str, List[str]]:
        """Get entity types grouped by domain for a specific area."""
        try:
            _LOGGER.debug("Getting entity types for area: %s", area_id)
            
            if self._area_topology.enabled:
                return await self._area_topology.get_entity_types_by_area(area_id)
            else:
                # Fallback implementation
                entities = await self.get_entities_by_area(area_id)
                entity_types = {}
                for entity in entities:
                    if isinstance(entity, dict) and "entity_id" in entity:
                        domain = entity["entity_id"].split(".")[0]
                        if domain not in entity_types:
                            entity_types[domain] = []
                        entity_types[domain].append(entity["entity_id"])
                return entity_types
                
        except Exception as e:
            _LOGGER.exception("Error getting entity types by area: %s", str(e))
            return {"error": f"Error getting entity types by area: {str(e)}"}

    async def get_floor_topology(self) -> Dict[str, Any]:
        """Get floor topology information including areas and entities per floor."""
        try:
            _LOGGER.debug("Getting floor topology information")
            
            if self._area_topology.enabled:
                return await self._area_topology.get_floor_topology()
            else:
                # Fallback implementation
                area_registry = await self.get_area_registry()
                if isinstance(area_registry, dict) and "error" not in area_registry:
                    floor_topology = {}
                    for area_id, area_info in area_registry.items():
                        floor_id = area_info.get("floor_id", "unknown")
                        if floor_id not in floor_topology:
                            floor_topology[floor_id] = {
                                "areas": [],
                                "entity_count": 0
                            }
                        floor_topology[floor_id]["areas"].append({
                            "area_id": area_id,
                            "name": area_info.get("name", "Unknown")
                        })
                    return floor_topology
                else:
                    return {"error": "Could not retrieve area registry"}
                    
        except Exception as e:
            _LOGGER.exception("Error getting floor topology: %s", str(e))
            return {"error": f"Error getting floor topology: {str(e)}"}

    async def get_entities_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get entities by category (e.g., 'lighting', 'security')."""
        try:
            _LOGGER.debug("Getting entities for category: %s", category)
            if self._entity_relationships.enabled:
                entity_ids = await self._entity_relationships.get_entities_by_category(category)
                
                # Get state information for each entity
                result = []
                for entity_id in entity_ids:
                    state_info = await self.get_entity_state(entity_id)
                    if not state_info.get("error"):
                        result.append(state_info)
                return result
            else:
                return {"error": "Entity relationship service is not enabled"}
        except Exception as e:
            _LOGGER.exception("Error getting entities by category: %s", str(e))
            return {"error": f"Error getting entities by category: {str(e)}"}

    async def get_related_entities(self, entity_id: str) -> Dict[str, Any]:
        """Get entities related to a specific entity."""
        try:
            _LOGGER.debug("Getting related entities for: %s", entity_id)
            if self._entity_relationships.enabled:
                return await self._entity_relationships.get_related_entities(entity_id)
            else:
                return {"error": "Entity relationship service is not enabled"}
        except Exception as e:
            _LOGGER.exception("Error getting related entities: %s", str(e))
            return {"error": f"Error getting related entities: {str(e)}"}

    async def get_person_data(self) -> List[Dict]:
        """Get person tracking information"""
        _LOGGER.debug("Requesting person tracking information")
        try:
            result = []
            for state in self.hass.states.async_all("person"):
                result.append(
                    {
                        "entity_id": state.entity_id,
                        "name": state.attributes.get("friendly_name", state.entity_id),
                        "state": state.state,
                        "latitude": state.attributes.get("latitude"),
                        "longitude": state.attributes.get("longitude"),
                        "source": state.attributes.get("source"),
                        "gps_accuracy": state.attributes.get("gps_accuracy"),
                        "last_changed": (
                            state.last_changed.isoformat()
                            if state.last_changed
                            else None
                        ),
                    }
                )
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
                self.hass,
                1,
                entity_id,
                True,
                set(),
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
                    "sum": stat_data.get("sum"),
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
                result.append(
                    {
                        "entity_id": state.entity_id,
                        "name": state.attributes.get("friendly_name", state.entity_id),
                        "last_activated": state.attributes.get("last_activated"),
                        "icon": state.attributes.get("icon"),
                        "last_changed": (
                            state.last_changed.isoformat()
                            if state.last_changed
                            else None
                        ),
                    }
                )
            return result
        except Exception as e:
            _LOGGER.exception("Error getting scene configurations: %s", str(e))
            return [{"error": f"Error getting scene configurations: {str(e)}"}]

    async def get_weather_data(self) -> Dict[str, Any]:
        """Get weather data from any available weather entity in the system."""
        try:
            # Find all weather entities
            weather_entities = [
                state
                for state in self.hass.states.async_all()
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
            _LOGGER.debug(
                "Available weather attributes: %s", json.dumps(all_attributes)
            )

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
                    "wind_bearing": day.get("wind_bearing"),
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
                "forecast_available": len(processed_forecast) > 0,
            }

            # Log the processed data for debugging
            _LOGGER.debug(
                "Processed weather data: %s",
                json.dumps(
                    {"current": current, "forecast_count": len(processed_forecast)}
                ),
            )

            return {"current": current, "forecast": processed_forecast}
        except Exception as e:
            _LOGGER.exception("Error getting weather data: %s", str(e))
            return {"error": f"Error getting weather data: {str(e)}"}

    async def create_automation(
        self, automation_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new automation with validation and sanitization."""
        try:
            _LOGGER.debug(
                "Creating automation with config: %s", json.dumps(automation_config)
            )

            # Validate required fields
            if not all(
                key in automation_config for key in ["alias", "trigger", "action"]
            ):
                return {"error": "Missing required fields in automation configuration"}

            # Sanitize configuration
            sanitized_config = self._sanitize_automation_config(automation_config)

            # Generate a unique ID for the automation
            automation_id = f"ai_agent_auto_{int(time.time() * 1000)}"

            # Create the automation entry
            automation_entry = {
                "id": automation_id,
                "alias": sanitized_config["alias"],
                "description": sanitized_config.get("description", ""),
                "trigger": sanitized_config["trigger"],
                "condition": sanitized_config.get("condition", []),
                "action": sanitized_config["action"],
                "mode": sanitized_config.get("mode", "single"),
            }

            # Read current automations.yaml using async executor
            automations_path = self.hass.config.path("automations.yaml")
            try:
                current_automations = await self.hass.async_add_executor_job(
                    lambda: yaml.safe_load(open(automations_path, "r")) or []
                )
            except FileNotFoundError:
                current_automations = []

            # Check for duplicate automation names
            if any(
                auto.get("alias") == automation_entry["alias"]
                for auto in current_automations
            ):
                return {
                    "error": f"An automation with the name '{automation_entry['alias']}' already exists"
                }

            # Append new automation
            current_automations.append(automation_entry)

            # Write back to file using async executor
            await self.hass.async_add_executor_job(
                lambda: yaml.dump(
                    current_automations,
                    open(automations_path, "w"),
                    default_flow_style=False,
                )
            )

            # Reload automations
            await self.hass.services.async_call("automation", "reload")

            # Clear automation-related caches
            self._cache.clear()

            return {
                "success": True,
                "message": f"Automation '{automation_entry['alias']}' created successfully",
            }

        except Exception as e:
            _LOGGER.exception("Error creating automation: %s", str(e))
            return {"error": f"Error creating automation: {str(e)}"}

    async def get_dashboards(self) -> List[Dict[str, Any]]:
        """Get list of all dashboards."""
        try:
            _LOGGER.debug("Requesting all dashboards")

            # Get dashboards via WebSocket API
            ws_api = self.hass.data.get("websocket_api")
            if not ws_api:
                return [{"error": "WebSocket API not available"}]

            # Use the lovelace service to get dashboards
            try:
                from homeassistant.components.lovelace import CONF_DASHBOARDS
                from homeassistant.components.lovelace import DOMAIN as LOVELACE_DOMAIN

                # Get lovelace config
                lovelace_config = self.hass.data.get(LOVELACE_DOMAIN, {})
                dashboards = lovelace_config.get(CONF_DASHBOARDS, {})

                dashboard_list = []

                # Add default dashboard
                dashboard_list.append(
                    {
                        "url_path": None,
                        "title": "Overview",
                        "icon": "mdi:home",
                        "show_in_sidebar": True,
                        "require_admin": False,
                    }
                )

                # Add custom dashboards
                for url_path, config in dashboards.items():
                    dashboard_list.append(
                        {
                            "url_path": url_path,
                            "title": config.get("title", url_path),
                            "icon": config.get("icon", "mdi:view-dashboard"),
                            "show_in_sidebar": config.get("show_in_sidebar", True),
                            "require_admin": config.get("require_admin", False),
                        }
                    )

                _LOGGER.debug("Found %d dashboards", len(dashboard_list))
                return dashboard_list

            except Exception as e:
                _LOGGER.warning("Could not get dashboards via lovelace: %s", str(e))
                return [{"error": f"Could not retrieve dashboards: {str(e)}"}]

        except Exception as e:
            _LOGGER.exception("Error getting dashboards: %s", str(e))
            return [{"error": f"Error getting dashboards: {str(e)}"}]

    async def get_dashboard_config(
        self, dashboard_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get configuration of a specific dashboard."""
        try:
            _LOGGER.debug(
                "Requesting dashboard config for: %s", dashboard_url or "default"
            )

            # Import the websocket handler
            from homeassistant.components.lovelace import websocket_api as lovelace_ws
            from homeassistant.components.websocket_api import require_admin

            # Create a mock websocket connection for internal use
            class MockConnection:
                def __init__(self, hass):
                    self.hass = hass
                    self.user = None

                def send_message(self, message):
                    pass

            # Get dashboard configuration
            try:
                from homeassistant.components.lovelace import DOMAIN as LOVELACE_DOMAIN

                # Dashboard import - this may vary by Home Assistant version
                LovelaceDashboard = None  # type: ignore[misc,assignment]

                # Get the dashboard
                lovelace_config = self.hass.data.get(LOVELACE_DOMAIN, {})

                if dashboard_url is None:
                    # Get default dashboard
                    dashboard = lovelace_config.get("default_dashboard")
                    if dashboard:
                        config = await dashboard.async_get_info()
                        return (
                            dict(config) if config else {"error": "No dashboard config"}
                        )
                    else:
                        return {"error": "Default dashboard not found"}
                else:
                    # Get custom dashboard
                    dashboards = lovelace_config.get("dashboards", {})
                    if dashboard_url in dashboards:
                        dashboard = dashboards[dashboard_url]
                        config = await dashboard.async_get_info()
                        return (
                            dict(config) if config else {"error": "No dashboard config"}
                        )
                    else:
                        return {"error": f"Dashboard '{dashboard_url}' not found"}

            except Exception as e:
                _LOGGER.warning("Could not get dashboard config: %s", str(e))
                return {"error": f"Could not retrieve dashboard config: {str(e)}"}

        except Exception as e:
            _LOGGER.exception("Error getting dashboard config: %s", str(e))
            return {"error": f"Error getting dashboard config: {str(e)}"}

    async def create_dashboard(
        self, dashboard_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new dashboard using Home Assistant's Lovelace WebSocket API."""
        try:
            _LOGGER.debug(
                "Creating dashboard with config: %s",
                json.dumps(dashboard_config, default=str),
            )

            # Validate required fields
            if not dashboard_config.get("title"):
                return {"error": "Dashboard title is required"}

            if not dashboard_config.get("url_path"):
                return {"error": "Dashboard URL path is required"}

            # Sanitize the URL path
            url_path = (
                dashboard_config["url_path"].lower().replace(" ", "-").replace("_", "-")
            )

            # Prepare dashboard configuration for Lovelace
            dashboard_data = {
                "title": dashboard_config["title"],
                "icon": dashboard_config.get("icon", "mdi:view-dashboard"),
                "show_in_sidebar": dashboard_config.get("show_in_sidebar", True),
                "require_admin": dashboard_config.get("require_admin", False),
                "views": dashboard_config.get("views", []),
            }

            try:
                # Create dashboard file directly - this is the most reliable method
                import os

                import yaml

                # Create the dashboard YAML file
                lovelace_config_file = self.hass.config.path(
                    f"ui-lovelace-{url_path}.yaml"
                )

                # Use async_add_executor_job to perform file I/O asynchronously
                def write_dashboard_file():
                    with open(lovelace_config_file, "w") as f:
                        yaml.dump(
                            dashboard_data,
                            f,
                            default_flow_style=False,
                            allow_unicode=True,
                        )

                await self.hass.async_add_executor_job(write_dashboard_file)

                _LOGGER.info(
                    "Successfully created dashboard file: %s", lovelace_config_file
                )

                # Now update configuration.yaml
                try:
                    config_file = self.hass.config.path("configuration.yaml")
                    dashboard_config_entry = {
                        url_path: {
                            "mode": "yaml",
                            "title": dashboard_config["title"],
                            "icon": dashboard_config.get("icon", "mdi:view-dashboard"),
                            "show_in_sidebar": dashboard_config.get(
                                "show_in_sidebar", True
                            ),
                            "filename": f"ui-lovelace-{url_path}.yaml",
                        }
                    }

                    def update_config_file():
                        try:
                            with open(config_file, "r") as f:
                                content = f.read()

                            # Dashboard configuration to add
                            dashboard_yaml = f"""    {url_path}:
      mode: yaml
      title: {dashboard_config['title']}
      icon: {dashboard_config.get('icon', 'mdi:view-dashboard')}
      show_in_sidebar: {str(dashboard_config.get('show_in_sidebar', True)).lower()}
      filename: ui-lovelace-{url_path}.yaml"""

                            # Check if lovelace section exists
                            if "lovelace:" not in content:
                                # Add complete lovelace section at the end
                                lovelace_section = f"""
# Lovelace dashboards configuration added by AI Agent
lovelace:
  dashboards:
{dashboard_yaml}
"""
                                with open(config_file, "a") as f:
                                    f.write(lovelace_section)
                                return True

                            # If lovelace exists, check for dashboards section
                            lines = content.split("\n")
                            new_lines = []
                            dashboard_added = False
                            in_lovelace = False
                            lovelace_indent = 0

                            for i, line in enumerate(lines):
                                new_lines.append(line)

                                # Detect lovelace section
                                if (
                                    line.strip() == "lovelace:"
                                    or line.strip().startswith("lovelace:")
                                ):
                                    in_lovelace = True
                                    lovelace_indent = len(line) - len(line.lstrip())
                                    continue

                                # If we're in lovelace section
                                if in_lovelace:
                                    current_indent = (
                                        len(line) - len(line.lstrip())
                                        if line.strip()
                                        else 0
                                    )

                                    # If we hit another top-level section, we're out of lovelace
                                    if (
                                        line.strip()
                                        and current_indent <= lovelace_indent
                                        and not line.startswith(" ")
                                    ):
                                        if line.strip() != "lovelace:":
                                            in_lovelace = False

                                    # Look for dashboards section
                                    if in_lovelace and "dashboards:" in line:
                                        # Add our dashboard after the dashboards: line
                                        new_lines.append(dashboard_yaml)
                                        dashboard_added = True
                                        in_lovelace = False  # We're done
                                        break

                            # If we found lovelace but no dashboards section, add it
                            if not dashboard_added and "lovelace:" in content:
                                # Find lovelace section and add dashboards
                                new_lines = []
                                for line in lines:
                                    new_lines.append(line)
                                    if (
                                        line.strip() == "lovelace:"
                                        or line.strip().startswith("lovelace:")
                                    ):
                                        # Add dashboards section right after lovelace
                                        new_lines.append("  dashboards:")
                                        new_lines.append(dashboard_yaml)
                                        dashboard_added = True
                                        break

                            if dashboard_added:
                                with open(config_file, "w") as f:
                                    f.write("\n".join(new_lines))
                                return True
                            else:
                                # Last resort: append to end of file
                                with open(config_file, "a") as f:
                                    f.write(f"\n  dashboards:\n{dashboard_yaml}\n")
                                return True

                        except Exception as e:
                            _LOGGER.error(
                                "Failed to update configuration.yaml: %s", str(e)
                            )
                            # Fallback to simple append method
                            try:
                                with open(config_file, "r") as f:
                                    content = f.read()

                                # Check if lovelace section exists
                                if "lovelace:" not in content:
                                    # Add lovelace section
                                    lovelace_config = f"""
# Lovelace dashboards
lovelace:
  dashboards:
    {url_path}:
      mode: yaml
      title: {dashboard_config['title']}
      icon: {dashboard_config.get('icon', 'mdi:view-dashboard')}
      show_in_sidebar: {str(dashboard_config.get('show_in_sidebar', True)).lower()}
      filename: ui-lovelace-{url_path}.yaml
"""
                                    with open(config_file, "a") as f:
                                        f.write(lovelace_config)
                                else:
                                    # Add to existing lovelace section (simple approach)
                                    dashboard_entry = f"""    {url_path}:
      mode: yaml
      title: {dashboard_config['title']}
      icon: {dashboard_config.get('icon', 'mdi:view-dashboard')}
      show_in_sidebar: {str(dashboard_config.get('show_in_sidebar', True)).lower()}
      filename: ui-lovelace-{url_path}.yaml
"""
                                    # Find the dashboards section and add to it
                                    lines = content.split("\n")
                                    new_lines = []
                                    in_dashboards = False
                                    dashboards_indented = False

                                    for line in lines:
                                        new_lines.append(line)
                                        if (
                                            "dashboards:" in line
                                            and "lovelace"
                                            in content[: content.find(line)]
                                        ):
                                            in_dashboards = True
                                            # Add our dashboard entry after dashboards:
                                            new_lines.append(dashboard_entry.rstrip())
                                            in_dashboards = False

                                    # If we couldn't find dashboards section, add it under lovelace
                                    if not any("dashboards:" in line for line in lines):
                                        for i, line in enumerate(new_lines):
                                            if line.strip() == "lovelace:":
                                                new_lines.insert(i + 1, "  dashboards:")
                                                new_lines.insert(
                                                    i + 2, dashboard_entry.rstrip()
                                                )
                                                break

                                    with open(config_file, "w") as f:
                                        f.write("\n".join(new_lines))

                                return True
                            except Exception as fallback_error:
                                _LOGGER.error(
                                    "Fallback config update also failed: %s",
                                    str(fallback_error),
                                )
                                return False

                    config_updated = await self.hass.async_add_executor_job(
                        update_config_file
                    )

                    if config_updated:
                        success_message = f"""Dashboard '{dashboard_config['title']}' created successfully!

✅ Dashboard file created: ui-lovelace-{url_path}.yaml
✅ Configuration.yaml updated automatically

🔄 Please restart Home Assistant to see your new dashboard in the sidebar."""

                        return {
                            "success": True,
                            "message": success_message,
                            "url_path": url_path,
                            "restart_required": True,
                        }
                    else:
                        # Config update failed, provide manual instructions
                        config_instructions = f"""Dashboard '{dashboard_config['title']}' created successfully!

✅ Dashboard file created: ui-lovelace-{url_path}.yaml
⚠️  Could not automatically update configuration.yaml

Please manually add this to your configuration.yaml:

lovelace:
  dashboards:
    {url_path}:
      mode: yaml
      title: {dashboard_config['title']}
      icon: {dashboard_config.get('icon', 'mdi:view-dashboard')}
      show_in_sidebar: {str(dashboard_config.get('show_in_sidebar', True)).lower()}
      filename: ui-lovelace-{url_path}.yaml

Then restart Home Assistant to see your new dashboard in the sidebar."""

                        return {
                            "success": True,
                            "message": config_instructions,
                            "url_path": url_path,
                            "restart_required": True,
                        }

                except Exception as config_error:
                    _LOGGER.error(
                        "Error updating configuration.yaml: %s", str(config_error)
                    )
                    # Provide manual instructions as fallback
                    config_instructions = f"""Dashboard '{dashboard_config['title']}' created successfully!

✅ Dashboard file created: ui-lovelace-{url_path}.yaml
⚠️  Could not automatically update configuration.yaml

Please manually add this to your configuration.yaml:

lovelace:
  dashboards:
    {url_path}:
      mode: yaml
      title: {dashboard_config['title']}
      icon: {dashboard_config.get('icon', 'mdi:view-dashboard')}
      show_in_sidebar: {str(dashboard_config.get('show_in_sidebar', True)).lower()}
      filename: ui-lovelace-{url_path}.yaml

Then restart Home Assistant to see your new dashboard in the sidebar."""

                    return {
                        "success": True,
                        "message": config_instructions,
                        "url_path": url_path,
                        "restart_required": True,
                    }

            except Exception as e:
                _LOGGER.error("Failed to create dashboard file: %s", str(e))
                return {"error": f"Failed to create dashboard file: {str(e)}"}

        except Exception as e:
            _LOGGER.exception("Error creating dashboard: %s", str(e))
            return {"error": f"Error creating dashboard: {str(e)}"}

    async def update_dashboard(
        self, dashboard_url: str, dashboard_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an existing dashboard using Home Assistant's Lovelace WebSocket API."""
        try:
            _LOGGER.debug(
                "Updating dashboard %s with config: %s",
                dashboard_url,
                json.dumps(dashboard_config, default=str),
            )

            # Prepare updated dashboard configuration
            dashboard_data = {
                "title": dashboard_config.get("title", "Updated Dashboard"),
                "icon": dashboard_config.get("icon", "mdi:view-dashboard"),
                "show_in_sidebar": dashboard_config.get("show_in_sidebar", True),
                "require_admin": dashboard_config.get("require_admin", False),
                "views": dashboard_config.get("views", []),
            }

            try:
                # Update dashboard file directly
                import os

                import yaml

                # Try updating the YAML file
                dashboard_file = self.hass.config.path(
                    f"ui-lovelace-{dashboard_url}.yaml"
                )

                # Check if file exists asynchronously
                def check_file_exists():
                    return os.path.exists(dashboard_file)

                file_exists = await self.hass.async_add_executor_job(check_file_exists)

                if not file_exists:
                    dashboard_file = self.hass.config.path(
                        f"dashboards/{dashboard_url}.yaml"
                    )
                    file_exists = await self.hass.async_add_executor_job(
                        lambda: os.path.exists(dashboard_file)
                    )

                if file_exists:
                    # Use async_add_executor_job to perform file I/O asynchronously
                    def update_dashboard_file():
                        with open(dashboard_file, "w") as f:
                            yaml.dump(
                                dashboard_data,
                                f,
                                default_flow_style=False,
                                allow_unicode=True,
                            )

                    await self.hass.async_add_executor_job(update_dashboard_file)

                    _LOGGER.info(
                        "Successfully updated dashboard file: %s", dashboard_file
                    )
                    return {
                        "success": True,
                        "message": f"Dashboard '{dashboard_url}' updated successfully!",
                    }
                else:
                    return {"error": f"Dashboard file for '{dashboard_url}' not found"}

            except Exception as e:
                _LOGGER.error("Failed to update dashboard file: %s", str(e))
                return {"error": f"Failed to update dashboard file: {str(e)}"}

        except Exception as e:
            _LOGGER.exception("Error updating dashboard: %s", str(e))
            return {"error": f"Error updating dashboard: {str(e)}"}

    async def process_query(
        self, user_query: str, provider: Optional[str] = None, model: Optional[str] = None, structure: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process a user query with input validation and rate limiting."""
        try:
            if not user_query or not isinstance(user_query, str):
                return {"success": False, "error": "Invalid query format"}

            # If Home Assistant passed a structured-output schema, enforce JSON mode
            enforce_json = bool(structure)

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
                    "client_class": OpenAIClient,
                },
            }

            # Validate provider and get configuration
            if selected_provider not in provider_config:
                _LOGGER.warning(
                    f"Invalid provider {selected_provider}, falling back to llama"
                )
                selected_provider = "llama"

            provider_settings = provider_config[selected_provider]
            token = self.config.get(provider_settings["token_key"])

            # Validate token/URL
            if not token:
                error_msg = f"No {'URL' if selected_provider == 'local' else 'token'} configured for provider {selected_provider}"
                _LOGGER.error(error_msg)
                return {"success": False, "error": error_msg}

            # Initialize client
            try:
                if selected_provider == "local":
                    # LocalClient takes (url, model)
                    self.ai_client = provider_settings["client_class"](
                        url=token, model=provider_settings["model"]
                    )
                else:
                    # Other clients take (token, model)
                    self.ai_client = provider_settings["client_class"](
                        token=token, model=model or provider_settings["model"]
                    )
                _LOGGER.debug(
                    f"Initialized {selected_provider} client with model {provider_settings['model']}"
                )
            except Exception as e:
                error_msg = f"Error initializing {selected_provider} client: {str(e)}"
                _LOGGER.error(error_msg)
                return {"success": False, "error": error_msg}

            # Process the query with rate limiting and retries
            if not self._check_rate_limit():
                return {
                    "success": False,
                    "error": "Rate limit exceeded. Please wait before trying again.",
                }

            # Sanitize user input
            user_query = user_query.strip()[:1000]  # Limit length and trim whitespace

            _LOGGER.debug("Processing new query: %s", user_query)

            # Check cache for identical query
            cache_key = f"query_{hash(user_query)}"
            cached_result = self._get_cached_data(cache_key)
            if cached_result:
                return (
                    dict(cached_result)
                    if isinstance(cached_result, dict)
                    else {"error": "Invalid cached result"}
                )

            # Add system message to conversation if it's the first message
            if not self.conversation_history:
                _LOGGER.debug("Adding system message to new conversation")
                self.conversation_history.append(self.system_prompt)
                if enforce_json and structure:
                    # Inject strict JSON schema instruction for AI Task
                    schema_instruction = (
                        "You MUST return a single valid JSON object that exactly matches this schema:\n"
                        f"{json.dumps(structure, indent=2)}\n"
                        "Do NOT wrap the JSON in code blocks, add explanations, or include any text outside the JSON."
                    )
                    self.conversation_history.append({"role": "system", "content": schema_instruction})

            # Add user query to conversation
            self.conversation_history.append({"role": "user", "content": user_query})
            _LOGGER.debug("Added user query to conversation history")

            max_iterations = 5  # Prevent infinite loops
            iteration = 0

            while iteration < max_iterations:
                iteration += 1
                _LOGGER.debug(f"Processing iteration {iteration} of {max_iterations}")

                try:
                    # Get AI response
                    _LOGGER.debug("Requesting response from AI provider")
                    response = await self._get_ai_response(enforce_json=enforce_json)
                    _LOGGER.debug("Received response from AI provider: %s", response)

                    try:
                        # Try to parse the response as JSON with simplified approach
                        response_clean = response.strip()

                        # Remove potential BOM and other invisible characters
                        import codecs

                        if response_clean.startswith(codecs.BOM_UTF8.decode("utf-8")):
                            response_clean = response_clean[1:]

                        # Remove other common invisible characters
                        invisible_chars = [
                            "\ufeff",
                            "\u200b",
                            "\u200c",
                            "\u200d",
                            "\u2060",
                        ]
                        for char in invisible_chars:
                            response_clean = response_clean.replace(char, "")

                        _LOGGER.debug(
                            "Cleaned response length: %d", len(response_clean)
                        )
                        _LOGGER.debug(
                            "Cleaned response first 100 chars: %s", response_clean[:100]
                        )
                        _LOGGER.debug(
                            "Cleaned response last 100 chars: %s", response_clean[-100:]
                        )

                        # Simple strategy: try to parse the cleaned response directly
                        response_data = None
                        try:
                            _LOGGER.debug("Attempting basic JSON parse...")
                            response_data = json.loads(response_clean)
                            _LOGGER.debug("Basic JSON parse succeeded!")
                        except json.JSONDecodeError as e:
                            _LOGGER.warning("Basic JSON parse failed: %s", str(e))
                            _LOGGER.debug("JSON error position: %d", e.pos)
                            if e.pos < len(response_clean):
                                _LOGGER.debug(
                                    "Character at error position: %s (ord: %d)",
                                    repr(response_clean[e.pos]),
                                    ord(response_clean[e.pos]),
                                )
                                _LOGGER.debug(
                                    "Context around error: %s",
                                    repr(
                                        response_clean[max(0, e.pos - 10) : e.pos + 10]
                                    ),
                                )

                            # Fallback: try to extract JSON by finding the first { and last }
                            json_start = response_clean.find("{")
                            json_end = response_clean.rfind("}")

                            if (
                                json_start != -1
                                and json_end != -1
                                and json_end > json_start
                            ):
                                json_part = response_clean[json_start : json_end + 1]
                                _LOGGER.debug(
                                    "Trying fallback extraction from pos %d to %d",
                                    json_start,
                                    json_end,
                                )
                                _LOGGER.debug("Extracted JSON: %s", json_part[:200])

                                try:
                                    response_data = json.loads(json_part)
                                    _LOGGER.debug("Fallback JSON extraction succeeded!")
                                except json.JSONDecodeError as e2:
                                    _LOGGER.warning(
                                        "Fallback JSON extraction also failed: %s",
                                        str(e2),
                                    )
                                    raise e  # Re-raise the original error
                            else:
                                _LOGGER.warning(
                                    "Could not find JSON boundaries in response"
                                )
                                raise e  # Re-raise the original error

                        if response_data is None:
                            raise json.JSONDecodeError(
                                "All parsing strategies failed", response_clean, 0
                            )

                        _LOGGER.debug("Successfully parsed JSON response")
                        _LOGGER.debug(
                            "Parsed response type: %s",
                            response_data.get("request_type", "unknown"),
                        )

                        # Check if this is a data request (either format)
                        data_request_types = [
                            "get_entity_state",
                            "get_entities_by_domain",
                            "get_entities_by_area",
                            "get_entities",
                            "get_calendar_events",
                            "get_automations",
                            "get_entity_registry",
                            "get_device_registry",
                            "get_weather_data",
                            "get_area_registry",
                            "get_entity_types_by_area",
                            "get_floor_topology",
                            "get_entities_by_category",
                            "get_related_entities",
                            "get_history",
                            "get_logbook_entries",
                            "get_person_data",
                            "get_statistics",
                            "get_scenes",
                            "get_dashboards",
                            "get_dashboard_config",
                            "set_entity_state",
                            "create_automation",
                            "create_dashboard",
                            "update_dashboard",
                            "analyze_image",
                            "analyze_video",
                            "web_search",
                        ]

                        if (
                            response_data.get("request_type") == "data_request"
                            or response_data.get("request_type") in data_request_types
                        ):
                            # Handle data request (both standard format and direct request type)
                            if response_data.get("request_type") == "data_request":
                                request_type = response_data.get("request")
                            else:
                                request_type = response_data.get("request_type")
                            parameters = response_data.get("parameters", {})
                            _LOGGER.debug(
                                "Processing data request: %s with parameters: %s",
                                request_type,
                                json.dumps(parameters),
                            )

                            # Add AI's response to conversation history
                            self.conversation_history.append(
                                {
                                    "role": "assistant",
                                    "content": json.dumps(
                                        response_data
                                    ),  # Store clean JSON
                                }
                            )

                            # Get requested data
                            data: Union[Dict[str, Any], List[Dict[str, Any]]]
                            if request_type == "get_entity_state":
                                data = await self.get_entity_state(
                                    parameters.get("entity_id")
                                )
                            elif request_type == "get_entities_by_domain":
                                data = await self.get_entities_by_domain(
                                    parameters.get("domain")
                                )
                            elif request_type == "get_entities_by_area":
                                data = await self.get_entities_by_area(
                                    parameters.get("area_id")
                                )
                            elif request_type == "get_entities":
                                data = await self.get_entities(
                                    area_id=parameters.get("area_id"),
                                    area_ids=parameters.get("area_ids"),
                                )
                            elif request_type == "get_calendar_events":
                                data = await self.get_calendar_events(
                                    parameters.get("entity_id")
                                )
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
                            elif request_type == "get_entity_types_by_area":
                                data = await self.get_entity_types_by_area(
                                    parameters.get("area_id")
                                )
                            elif request_type == "get_floor_topology":
                                data = await self.get_floor_topology()
                            elif request_type == "get_floor_topology":
                                data = await self.get_floor_topology()
                            elif request_type == "get_entities_by_category":
                                data = await self.get_entities_by_category(
                                    parameters.get("category")
                                )
                            elif request_type == "get_related_entities":
                                data = await self.get_related_entities(
                                    parameters.get("entity_id")
                                )
                            elif request_type == "get_history":
                                data = await self.get_history(
                                    parameters.get("entity_id"),
                                    parameters.get("hours", 24),
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
                            elif request_type == "get_dashboards":
                                data = await self.get_dashboards()
                            elif request_type == "get_dashboard_config":
                                data = await self.get_dashboard_config(
                                    parameters.get("dashboard_url")
                                )
                            elif request_type == "set_entity_state":
                                data = await self.set_entity_state(
                                    parameters.get("entity_id"),
                                    parameters.get("state"),
                                    parameters.get("attributes"),
                                )
                            elif request_type == "create_automation":
                                data = await self.create_automation(
                                    parameters.get("automation")
                                )
                            elif request_type == "create_dashboard":
                                data = await self.create_dashboard(
                                    parameters.get("dashboard_config")
                                )
                            elif request_type == "update_dashboard":
                                data = await self.update_dashboard(
                                    parameters.get("dashboard_url"),
                                    parameters.get("dashboard_config"),
                                )
                            elif request_type == "analyze_image":
                                data = await self.analyze_image(
                                    parameters.get("image_source"),
                                    parameters.get("prompt", "Analyze this image")
                                )
                            elif request_type == "analyze_video":
                                data = await self.analyze_video(
                                    parameters.get("video_source"),
                                    parameters.get("prompt", "Analyze this video")
                                )
                            elif request_type == "web_search":
                                data = await self.web_search(
                                    parameters.get("query"),
                                    parameters.get("count", 5),
                                    parameters.get("search_recency_filter", "noLimit")
                                )
                            else:
                                data = {
                                    "error": f"Unknown request type: {request_type}"
                                }
                                _LOGGER.warning(
                                    "Unknown request type: %s", request_type
                                )

                            # Check if any data request resulted in an error
                            if isinstance(data, dict) and "error" in data:
                                return {"success": False, "error": data["error"]}
                            elif isinstance(data, list) and any(
                                "error" in item
                                for item in data
                                if isinstance(item, dict)
                            ):
                                errors = [
                                    item["error"]
                                    for item in data
                                    if isinstance(item, dict) and "error" in item
                                ]
                                return {"success": False, "error": "; ".join(errors)}

                            _LOGGER.debug(
                                "Retrieved data for request: %s",
                                json.dumps(data, default=str),
                            )

                            # Add data to conversation as a system message
                            self.conversation_history.append(
                                {
                                    "role": "system",
                                    "content": json.dumps({"data": data}, default=str),
                                }
                            )
                            continue

                        elif response_data.get("request_type") == "final_response":
                            # Add final response to conversation history
                            self.conversation_history.append(
                                {
                                    "role": "assistant",
                                    "content": json.dumps(
                                        response_data
                                    ),  # Store clean JSON
                                }
                            )

                            # Return final response
                            _LOGGER.debug(
                                "Received final response: %s",
                                response_data.get("response"),
                            )
                            result = {
                                "success": True,
                                "answer": response_data.get("response", ""),
                            }
                            self._set_cached_data(cache_key, result)
                            return result
                        elif (
                            response_data.get("request_type") == "automation_suggestion"
                        ):
                            # Add automation suggestion to conversation history
                            self.conversation_history.append(
                                {
                                    "role": "assistant",
                                    "content": json.dumps(
                                        response_data
                                    ),  # Store clean JSON
                                }
                            )

                            # Return automation suggestion
                            _LOGGER.debug(
                                "Received automation suggestion: %s",
                                json.dumps(response_data.get("automation")),
                            )
                            result = {
                                "success": True,
                                "answer": json.dumps(response_data),
                            }
                            self._set_cached_data(cache_key, result)
                            return result
                        elif (
                            response_data.get("request_type") == "dashboard_suggestion"
                        ):
                            # Add dashboard suggestion to conversation history
                            self.conversation_history.append(
                                {
                                    "role": "assistant",
                                    "content": json.dumps(
                                        response_data
                                    ),  # Store clean JSON
                                }
                            )

                            # Return dashboard suggestion
                            _LOGGER.debug(
                                "Received dashboard suggestion: %s",
                                json.dumps(response_data.get("dashboard")),
                            )
                            result = {
                                "success": True,
                                "answer": json.dumps(response_data),
                            }
                            self._set_cached_data(cache_key, result)
                            return result
                        elif response_data.get("request_type") in [
                            "get_entities",
                            "get_entities_by_area",
                        ]:
                            # Handle direct get_entities request (for backward compatibility)
                            parameters = response_data.get("parameters", {})
                            _LOGGER.debug(
                                "Processing direct get_entities request with parameters: %s",
                                json.dumps(parameters),
                            )

                            # Add AI's response to conversation history
                            self.conversation_history.append(
                                {
                                    "role": "assistant",
                                    "content": json.dumps(
                                        response_data
                                    ),  # Store clean JSON
                                }
                            )

                            # Get entities data
                            if response_data.get("request_type") == "get_entities":
                                data = await self.get_entities(
                                    area_id=parameters.get("area_id"),
                                    area_ids=parameters.get("area_ids"),
                                )
                            else:  # get_entities_by_area
                                data = await self.get_entities_by_area(
                                    parameters.get("area_id")
                                )

                            _LOGGER.debug(
                                "Retrieved %d entities",
                                len(data) if isinstance(data, list) else 1,
                            )

                            # Add data to conversation as a system message
                            self.conversation_history.append(
                                {
                                    "role": "system",
                                    "content": json.dumps({"data": data}, default=str),
                                }
                            )
                            continue
                        elif response_data.get("request_type") == "call_service":
                            # Handle service call request
                            domain = response_data.get("domain")
                            service = response_data.get("service")
                            target = response_data.get("target", {})
                            service_data = response_data.get("service_data", {})

                            # Resolve nested requests in target
                            if target and "entity_id" in target:
                                entity_id_value = target["entity_id"]
                                if (
                                    isinstance(entity_id_value, dict)
                                    and "request_type" in entity_id_value
                                ):
                                    # This is a nested request, resolve it
                                    nested_request_type = entity_id_value.get(
                                        "request_type"
                                    )
                                    nested_parameters = entity_id_value.get(
                                        "parameters", {}
                                    )

                                    _LOGGER.debug(
                                        "Resolving nested request: %s with parameters: %s",
                                        nested_request_type,
                                        json.dumps(nested_parameters),
                                    )

                                    # Resolve the nested request
                                    if nested_request_type == "get_entities":
                                        entities_data = await self.get_entities(
                                            area_id=nested_parameters.get("area_id"),
                                            area_ids=nested_parameters.get("area_ids"),
                                        )
                                    elif nested_request_type == "get_entities_by_area":
                                        entities_data = await self.get_entities_by_area(
                                            nested_parameters.get("area_id")
                                        )
                                    elif (
                                        nested_request_type == "get_entities_by_domain"
                                    ):
                                        entities_data = (
                                            await self.get_entities_by_domain(
                                                nested_parameters.get("domain")
                                            )
                                        )
                                    else:
                                        _LOGGER.error(
                                            "Unsupported nested request type: %s",
                                            nested_request_type,
                                        )
                                        return {
                                            "success": False,
                                            "error": f"Unsupported nested request type: {nested_request_type}",
                                        }

                                    # Extract entity IDs from the resolved data
                                    if isinstance(entities_data, list):
                                        entity_ids = [
                                            entity.get("entity_id")
                                            for entity in entities_data
                                            if entity.get("entity_id")
                                        ]
                                        target["entity_id"] = entity_ids
                                        _LOGGER.debug(
                                            "Resolved nested request to entity IDs: %s",
                                            entity_ids,
                                        )
                                    else:
                                        _LOGGER.error(
                                            "Nested request returned unexpected data format"
                                        )
                                        return {
                                            "success": False,
                                            "error": "Nested request returned unexpected data format",
                                        }

                            # Handle backward compatibility with old format
                            if not domain or not service:
                                request = response_data.get("request")
                                parameters = response_data.get("parameters", {})

                                if request and "entity_id" in parameters:
                                    entity_id = parameters["entity_id"]
                                    # Infer domain from entity_id
                                    if "." in entity_id:
                                        domain = entity_id.split(".")[0]
                                        service = request
                                        target = {"entity_id": entity_id}
                                        # Remove entity_id from parameters to avoid duplication
                                        service_data = {
                                            k: v
                                            for k, v in parameters.items()
                                            if k != "entity_id"
                                        }
                                        _LOGGER.debug(
                                            "Converted old format: domain=%s, service=%s",
                                            domain,
                                            service,
                                        )

                            _LOGGER.debug(
                                "Processing service call: %s.%s with target: %s and data: %s",
                                domain,
                                service,
                                json.dumps(target),
                                json.dumps(service_data),
                            )

                            # Add AI's response to conversation history
                            self.conversation_history.append(
                                {
                                    "role": "assistant",
                                    "content": json.dumps(
                                        response_data
                                    ),  # Store clean JSON
                                }
                            )

                            # Call the service
                            data = await self.call_service(
                                domain, service, target, service_data
                            )

                            # Check if service call resulted in an error
                            if isinstance(data, dict) and "error" in data:
                                return {"success": False, "error": data["error"]}

                            _LOGGER.debug(
                                "Service call completed: %s",
                                json.dumps(data, default=str),
                            )

                            # Add data to conversation as a system message
                            self.conversation_history.append(
                                {
                                    "role": "system",
                                    "content": json.dumps({"data": data}, default=str),
                                }
                            )
                            continue
                        else:
                            _LOGGER.warning(
                                "Unknown response type: %s",
                                response_data.get("request_type"),
                            )
                            return {
                                "success": False,
                                "error": f"Unknown response type: {response_data.get('request_type')}",
                            }

                    except json.JSONDecodeError as e:
                        # Check if this is a local provider that might have already wrapped the response
                        provider = self.config.get("ai_provider", "unknown")
                        if provider == "local":
                            _LOGGER.debug(
                                "Local provider returned non-JSON response (this is normal and handled): %s",
                                response[:200],
                            )
                        else:
                            # Log more of the response to help with debugging for non-local providers
                            response_preview = (
                                response[:1000] if len(response) > 1000 else response
                            )
                            _LOGGER.warning(
                                "Failed to parse response as JSON: %s. Response length: %d. Response preview: %s",
                                str(e),
                                len(response),
                                response_preview,
                            )

                            # Log additional debugging information
                            _LOGGER.debug(
                                "First 50 characters as bytes: %s",
                                response[:50].encode("utf-8") if response else b"",
                            )
                            _LOGGER.debug(
                                "Response starts with: %s",
                                repr(response[:10]) if response else "None",
                            )
                            
                            # If we were enforcing JSON and got a parsing error, try a corrective retry
                            if enforce_json and iteration < max_iterations:
                                _LOGGER.warning(
                                    "JSON parsing failed despite enforce_json=True. Attempting corrective retry with explicit JSON instruction."
                                )
                                # Add an explicit system message asking for pure JSON
                                self.conversation_history.append({
                                    "role": "system",
                                    "content": "The previous response was not valid JSON. Please respond with ONLY a valid JSON object. Do not include any explanations, code blocks, or text outside the JSON."
                                })
                                continue  # Try again with the explicit instruction

                        # Also log the response to a separate debug file for detailed analysis (non-local providers only)
                        if provider != "local":
                            try:
                                import os

                                debug_dir = "/config/glm_agent_ha_debug"

                                def write_debug_file():
                                    if not os.path.exists(debug_dir):
                                        os.makedirs(debug_dir)

                                    import datetime

                                    timestamp = datetime.datetime.now().strftime(
                                        "%Y%m%d_%H%M%S"
                                    )
                                    debug_file = os.path.join(
                                        debug_dir, f"failed_response_{timestamp}.txt"
                                    )

                                    with open(debug_file, "w", encoding="utf-8") as f:
                                        f.write(f"Timestamp: {timestamp}\n")
                                        f.write(f"Provider: {provider}\n")
                                        f.write(f"Error: {str(e)}\n")
                                        f.write(f"Response length: {len(response)}\n")
                                        f.write(
                                            f"Response bytes: {response.encode('utf-8') if response else b''}\n"
                                        )
                                        f.write(f"Response repr: {repr(response)}\n")
                                        f.write(f"Full response:\n{response}\n")

                                    return debug_file

                                # Run file operations in executor to avoid blocking
                                debug_file = await self.hass.async_add_executor_job(
                                    write_debug_file
                                )
                                _LOGGER.info(
                                    "Failed response saved to debug file: %s",
                                    debug_file,
                                )
                            except Exception as debug_error:
                                _LOGGER.debug(
                                    "Could not save debug file: %s", str(debug_error)
                                )

                        # Check if this looks like a corrupted automation suggestion
                        if (
                            response.strip().startswith(
                                '{"request_type": "automation_suggestion'
                            )
                            and len(response) > 10000
                            and response.count("for its use in various fields") > 50
                        ):
                            _LOGGER.warning(
                                "Detected corrupted automation suggestion response with repetitive text"
                            )
                            result = {
                                "success": False,
                                "error": "AI generated corrupted automation response. Please try again with a more specific automation request.",
                            }
                            self._set_cached_data(cache_key, result)
                            return result

                        # If response is not valid JSON, try to wrap it as a final response
                        try:
                            # Truncate extremely long responses to prevent memory issues
                            response_to_wrap = response
                            if len(response) > 50000:
                                response_to_wrap = (
                                    response[:5000]
                                    + "... [Response truncated due to excessive length]"
                                )
                                _LOGGER.warning(
                                    "Truncated extremely long response from %d to 5000 characters",
                                    len(response),
                                )

                            wrapped_response = {
                                "request_type": "final_response",
                                "response": response_to_wrap,
                            }
                            result = {
                                "success": True,
                                "answer": json.dumps(wrapped_response),
                            }
                            _LOGGER.debug("Wrapped non-JSON response as final_response")
                        except Exception as wrap_error:
                            _LOGGER.error(
                                "Failed to wrap response: %s", str(wrap_error)
                            )
                            result = {
                                "success": False,
                                "error": f"Invalid response format: {str(e)}",
                            }

                        self._set_cached_data(cache_key, result)
                        return result

                except Exception as e:
                    _LOGGER.exception("Error processing AI response: %s", str(e))
                    return {
                        "success": False,
                        "error": f"Error processing AI response: {str(e)}",
                    }

            # If we've reached max iterations without a final response
            _LOGGER.warning("Reached maximum iterations without final response")
            result = {
                "success": False,
                "error": "Maximum iterations reached without final response",
            }
            self._set_cached_data(cache_key, result)
            return result

        except Exception as e:
            _LOGGER.exception("Error in process_query: %s", str(e))
            return {"success": False, "error": f"Error in process_query: {str(e)}"}

    async def _get_ai_response(self, enforce_json: bool = False) -> str:
        """Get response from the selected AI provider with retries and rate limiting."""
        if not self._check_rate_limit():
            raise Exception("Rate limit exceeded. Please try again later.")
        retry_count = 0
        last_error = None
        # Limit conversation history to last 10 messages to prevent token overflow
        recent_messages = (
            self.conversation_history[-10:]
            if len(self.conversation_history) > 10
            else self.conversation_history
        )
        # Ensure system prompt is always the first message
        if not recent_messages or recent_messages[0].get("role") != "system":
            recent_messages = [self.system_prompt] + recent_messages

        _LOGGER.debug("Sending %d messages to AI provider", len(recent_messages))
        _LOGGER.debug("AI provider: %s", self.config.get("ai_provider", "unknown"))
        _LOGGER.debug("Enforce JSON mode: %s", enforce_json)

        while retry_count < self._max_retries:
            try:
                _LOGGER.debug(
                    "Attempt %d/%d: Calling AI client",
                    retry_count + 1,
                    self._max_retries,
                )
                # Pass response_format to enforce JSON mode when needed
                response_format = {"type": "json_object"} if enforce_json else None
                response = await self.ai_client.get_response(
                    recent_messages,
                    response_format=response_format
                )
                _LOGGER.debug("Used response_format: %s", response_format)
                _LOGGER.debug(
                    "AI client returned response of length: %d", len(response or "")
                )
                _LOGGER.debug("AI response preview: %s", (response or "")[:200])

                # Check for extremely long responses that might indicate model issues
                if response and len(response) > 50000:
                    _LOGGER.warning(
                        "AI returned extremely long response (%d characters), this may indicate a model issue",
                        len(response),
                    )
                    # Check for repetitive patterns that indicate a corrupted response
                    if response.count("for its use in various fields") > 50:
                        _LOGGER.error(
                            "Detected corrupted repetitive response, aborting this iteration"
                        )
                        raise Exception(
                            "AI generated corrupted response with repetitive text. Please try again with a clearer request."
                        )

                # Check if response is empty
                if not response or response.strip() == "":
                    _LOGGER.warning(
                        "AI client returned empty response on attempt %d",
                        retry_count + 1,
                    )
                    if retry_count + 1 >= self._max_retries:
                        raise Exception(
                            "AI provider returned empty response after all retries"
                        )
                    else:
                        retry_count += 1
                        await asyncio.sleep(self._retry_delay * retry_count)
                        continue

                return str(response)
            except Exception as e:
                _LOGGER.error(
                    "AI client error on attempt %d: %s", retry_count + 1, str(e)
                )
                last_error = e
                retry_count += 1
                if retry_count < self._max_retries:
                    await asyncio.sleep(self._retry_delay * retry_count)
                continue
        raise Exception(
            f"Failed after {retry_count} retries. Last error: {str(last_error)}"
        )

    def clear_conversation_history(self) -> None:
        """Clear the conversation history and cache."""
        self.conversation_history = []
        self._cache.clear()
        _LOGGER.debug("Conversation history and cache cleared")

    async def set_entity_state(
        self, entity_id: str, state: str, attributes: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Set the state of an entity."""
        try:
            _LOGGER.debug(
                "Setting state for entity %s to %s with attributes: %s",
                entity_id,
                state,
                json.dumps(attributes or {}),
            )

            # Validate entity exists
            if not self.hass.states.get(entity_id):
                return {"error": f"Entity {entity_id} not found"}

            # Call the appropriate service based on the domain
            domain = entity_id.split(".")[0]

            if domain == "light":
                service = (
                    "turn_on" if state.lower() in ["on", "true", "1"] else "turn_off"
                )
                service_data = {"entity_id": entity_id}
                if attributes and service == "turn_on":
                    service_data.update(attributes)
                await self.hass.services.async_call("light", service, service_data)

            elif domain == "switch":
                service = (
                    "turn_on" if state.lower() in ["on", "true", "1"] else "turn_off"
                )
                await self.hass.services.async_call(
                    "switch", service, {"entity_id": entity_id}
                )

            elif domain == "cover":
                if state.lower() in ["open", "up"]:
                    service = "open_cover"
                elif state.lower() in ["close", "down"]:
                    service = "close_cover"
                elif state.lower() == "stop":
                    service = "stop_cover"
                else:
                    return {"error": f"Invalid state {state} for cover entity"}
                await self.hass.services.async_call(
                    "cover", service, {"entity_id": entity_id}
                )

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
                service = (
                    "turn_on" if state.lower() in ["on", "true", "1"] else "turn_off"
                )
                service_data = {"entity_id": entity_id}
                if attributes and service == "turn_on":
                    service_data.update(attributes)
                await self.hass.services.async_call("fan", service, service_data)

            else:
                # For other domains, try to set the state directly
                self.hass.states.async_set(entity_id, state, attributes or {})

            # Get the new state to confirm the change
            new_state = self.hass.states.get(entity_id)
            return {
                "success": True,
                "entity_id": entity_id,
                "new_state": new_state.state,
                "new_attributes": new_state.attributes,
            }

        except Exception as e:
            _LOGGER.exception("Error setting entity state: %s", str(e))
            return {"error": f"Error setting entity state: {str(e)}"}

    async def call_service(
        self,
        domain: str,
        service: str,
        target: Optional[Dict[str, Any]] = None,
        service_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Call a Home Assistant service."""
        try:
            _LOGGER.debug(
                "Calling service %s.%s with target: %s and data: %s",
                domain,
                service,
                json.dumps(target or {}),
                json.dumps(service_data or {}),
            )

            # Prepare the service call data
            call_data = {}

            # Add target entities if provided
            if target:
                if "entity_id" in target:
                    entity_ids = target["entity_id"]
                    if isinstance(entity_ids, list):
                        call_data["entity_id"] = entity_ids
                    else:
                        call_data["entity_id"] = [entity_ids]

                # Add other target properties
                for key, value in target.items():
                    if key != "entity_id":
                        call_data[key] = value

            # Add service data if provided
            if service_data:
                call_data.update(service_data)

            _LOGGER.debug("Final service call data: %s", json.dumps(call_data))

            # Call the service
            await self.hass.services.async_call(domain, service, call_data)

            # Get the updated states of affected entities
            result_entities = []
            if "entity_id" in call_data:
                for entity_id in call_data["entity_id"]:
                    state = self.hass.states.get(entity_id)
                    if state:
                        result_entities.append(
                            {
                                "entity_id": entity_id,
                                "state": state.state,
                                "attributes": dict(state.attributes),
                            }
                        )

            return {
                "success": True,
                "service": f"{domain}.{service}",
                "entities_affected": result_entities,
                "message": f"Successfully called {domain}.{service}",
            }

        except Exception as e:
            _LOGGER.exception(
                "Error calling service %s.%s: %s", domain, service, str(e)
            )
            return {"error": f"Error calling service {domain}.{service}: {str(e)}"}

    async def save_user_prompt_history(
        self, user_id: str, history: List[str]
    ) -> Dict[str, Any]:
        """Save user's prompt history to HA storage."""
        try:
            store: Store = Store(self.hass, 1, f"glm_agent_ha_history_{user_id}")
            await store.async_save({"history": history})
            return {"success": True}
        except Exception as e:
            _LOGGER.exception("Error saving prompt history: %s", str(e))
            return {"error": f"Error saving prompt history: {str(e)}"}

    async def load_user_prompt_history(self, user_id: str) -> Dict[str, Any]:
        """Load user's prompt history from HA storage."""
        try:
            store: Store = Store(self.hass, 1, f"glm_agent_ha_history_{user_id}")
            data = await store.async_load()
            history = data.get("history", []) if data else []
            return {"success": True, "history": history}
        except Exception as e:
            _LOGGER.exception("Error loading prompt history: %s", str(e))
            return {"error": f"Error loading prompt history: {str(e)}", "history": []}

    async def analyze_image(self, image_source: str, prompt: str = "Analyze this image") -> Dict[str, Any]:
        """Analyze an image using Z.AI MCP integration (Pro/Max plans only)."""
        try:
            _LOGGER.debug("Analyzing image with source: %s", image_source)
            
            if not self.mcp_manager.is_mcp_available():
                return {
                    "error": "Image analysis is only available with Pro or Max plans",
                    "plan_required": "pro"
                }
            
            parameters = {
                "image_source": image_source,
                "prompt": prompt
            }
            
            result = await self.mcp_manager.call_mcp_tool("image_analysis", parameters)
            _LOGGER.debug("Image analysis result: %s", result)
            return result
            
        except Exception as e:
            _LOGGER.exception("Error analyzing image: %s", str(e))
            return {"error": f"Error analyzing image: {str(e)}"}

    async def analyze_video(self, video_source: str, prompt: str = "Analyze this video") -> Dict[str, Any]:
        """Analyze a video using Z.AI MCP integration (Pro/Max plans only)."""
        try:
            _LOGGER.debug("Analyzing video with source: %s", video_source)
            
            if not self.mcp_manager.is_mcp_available():
                return {
                    "error": "Video analysis is only available with Pro or Max plans",
                    "plan_required": "pro"
                }
            
            parameters = {
                "video_source": video_source,
                "prompt": prompt
            }
            
            result = await self.mcp_manager.call_mcp_tool("video_analysis", parameters)
            _LOGGER.debug("Video analysis result: %s", result)
            return result
            
        except Exception as e:
            _LOGGER.exception("Error analyzing video: %s", str(e))
            return {"error": f"Error analyzing video: {str(e)}"}

    async def web_search(self, query: str, count: int = 5, search_recency_filter: str = "noLimit") -> Dict[str, Any]:
        """Search the web using Z.AI MCP integration (Pro/Max plans only)."""
        try:
            _LOGGER.debug("Performing web search for: %s", query)
            
            if not self.mcp_manager.is_mcp_available():
                return {
                    "error": "Web search is only available with Pro or Max plans",
                    "plan_required": "pro"
                }
            
            parameters = {
                "query": query,
                "count": count,
                "search_recency_filter": search_recency_filter
            }
            
            result = await self.mcp_manager.call_mcp_tool("webSearchPrime", parameters)
            _LOGGER.debug("Web search result: %s", result)
            return result
            
        except Exception as e:
            _LOGGER.exception("Error performing web search: %s", str(e))
            return {"error": f"Error performing web search: {str(e)}"}

    async def initialize_mcp_integration(self) -> bool:
        """Initialize MCP integration for Pro/Max plans."""
        try:
            if self.mcp_manager.is_mcp_available():
                success = await self.mcp_manager.initialize_mcp_connections()
                if success:
                    _LOGGER.info("MCP integration initialized successfully")
                else:
                    _LOGGER.warning("Failed to initialize some MCP connections")
                return success
            else:
                _LOGGER.debug("MCP integration not available for current plan")
                return False
        except Exception as e:
            _LOGGER.exception("Error initializing MCP integration: %s", str(e))
            return False

    async def get_mcp_status(self) -> Dict[str, Any]:
        """Get the status of MCP integration."""
        try:
            return self.mcp_manager.get_mcp_status()
        except Exception as e:
            _LOGGER.exception("Error getting MCP status: %s", str(e))
            return {"error": f"Error getting MCP status: {str(e)}"}
