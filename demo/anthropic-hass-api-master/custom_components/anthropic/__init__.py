"""The Anthropic integration."""
from __future__ import annotations

import logging
import aiohttp
import asyncio
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

# Define our own APIError class for compatibility
class APIError(Exception):
    """API Error."""

    def __init__(self, message, type, status_code):
        """Initialize the error."""
        self.message = message
        self.type = type
        self.status_code = status_code
        super().__init__(message)

from homeassistant.components import conversation as ha_conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_LLM_HASS_API, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_CHAT_MODEL,
    CONF_CONTROL_HA,
    CONF_MAX_TOKENS,
    CONF_PROMPT,
    CONF_RECOMMENDED_SETTINGS,
    CONF_TEMPERATURE,
    DEFAULT_CONTROL_HA,
    DEFAULT_MAX_TOKENS,
    DEFAULT_PROMPT,
    DEFAULT_RECOMMENDED_SETTINGS,
    DEFAULT_TEMPERATURE,
    DOMAIN,
    AnthropicModels,
)
from .conversation_agent import AnthropicAgent

_LOGGER = logging.getLogger(__name__)

PLATFORMS = (Platform.CONVERSATION,)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Anthropic component."""
    hass.data[DOMAIN] = {}
    return True


# Response classes for Anthropic API
class ResponseContent:
    """Response content object."""
    
    def __init__(self, text):
        """Initialize the response content."""
        self.text = text
        self.type = "text"

class ToolUseContent:
    """Tool use content object."""
    
    def __init__(self, id, name, input_data):
        """Initialize the tool use content."""
        self.id = id
        self.name = name
        self.input = input_data
        self.type = "tool_use"

class Response:
    """Response object."""
    
    def __init__(self, content):
        """Initialize the response."""
        self.content = content

class Messages:
    """Messages API wrapper."""
    
    def __init__(self, api_key):
        """Initialize the messages wrapper."""
        self.api_key = api_key
    
    async def create(self, model, max_tokens, temperature, system, messages, tools=None):
        """Create a message asynchronously."""
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",  # This is the minimum supported version
            "content-type": "application/json",
        }
        data = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system,
            "messages": messages,
        }
        
        # Add tools if provided
        if tools:
            data["tools"] = tools
        
        _LOGGER.debug("Making API request to Anthropic: %s", data)
        
        async with aiohttp.ClientSession() as session:
            try:
                # Use asyncio.timeout instead of async_timeout
                async with asyncio.timeout(30):
                    async with session.post(url, headers=headers, json=data) as response:
                        if response.status != 200:
                            error_message = f"API request failed with status {response.status}"
                            try:
                                error_data = await response.json()
                                if "error" in error_data:
                                    error_message = f"{error_message}: {error_data['error'].get('message', '')}"
                            except Exception:
                                error_message = f"{error_message}: {await response.text()}"
                            
                            raise APIError(
                                message=error_message,
                                type="api_error",
                                status_code=response.status,
                            )
                        
                        # Parse the response
                        response_data = await response.json()
                        _LOGGER.debug("Received API response from Anthropic: %s", response_data)
                        
                        # Extract the content from the response
                        content_items = []
                        api_content = response_data.get("content", [])
                        
                        if api_content and isinstance(api_content, list):
                            for content_item in api_content:
                                if isinstance(content_item, dict):
                                    item_type = content_item.get("type")
                                    if item_type == "text":
                                        content_items.append(ResponseContent(content_item.get("text", "")))
                                    elif item_type == "tool_use":
                                        content_items.append(ToolUseContent(
                                            content_item.get("id", ""),
                                            content_item.get("name", ""),
                                            content_item.get("input", {})
                                        ))
                        
                        # If we couldn't extract any content, provide a fallback
                        if not content_items:
                            content_text = ""
                            # Try to get text from the top level
                            if "text" in response_data:
                                content_text = response_data["text"]
                            else:
                                content_text = "I'm sorry, I couldn't generate a proper response."
                                _LOGGER.warning("Could not extract content from Anthropic response: %s", response_data)
                            
                            content_items.append(ResponseContent(content_text))
                        
                        return Response(content_items)
            except asyncio.TimeoutError:
                raise APIError(
                    message="Request timed out",
                    type="timeout_error",
                    status_code=408,
                )
            except aiohttp.ClientError as err:
                raise APIError(
                    message=f"Request error: {err}",
                    type="request_error",
                    status_code=500,
                )
            except Exception as err:
                _LOGGER.error("Error parsing Anthropic response: %s", err)
                raise APIError(
                    message=f"Error parsing response: {err}",
                    type="parse_error",
                    status_code=500,
                )

class AnthropicWrapper:
    """Simple wrapper for Anthropic API."""
    
    def __init__(self, api_key):
        """Initialize the wrapper."""
        self.api_key = api_key
        self.messages = Messages(api_key)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Anthropic from a config entry."""
    try:
        # Create our wrapper for the Anthropic client
        client = AnthropicWrapper(entry.data[CONF_API_KEY])
    except Exception as err:
        _LOGGER.error("Failed to initialize Anthropic client: %s", err)
        raise ConfigEntryNotReady from err

    # Set default options if not already set
    if not entry.options:
        options = {
            CONF_PROMPT: DEFAULT_PROMPT,
            CONF_CONTROL_HA: DEFAULT_CONTROL_HA,
            CONF_RECOMMENDED_SETTINGS: DEFAULT_RECOMMENDED_SETTINGS,
            CONF_CHAT_MODEL: AnthropicModels.default(),
            CONF_MAX_TOKENS: DEFAULT_MAX_TOKENS,
            CONF_TEMPERATURE: DEFAULT_TEMPERATURE,
            # Don't set CONF_LLM_HASS_API by default
        }
        hass.config_entries.async_update_entry(entry, options=options)

    # Store the client in hass.data
    hass.data[DOMAIN][entry.entry_id] = client

    # Forward the entry setup to the conversation platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok