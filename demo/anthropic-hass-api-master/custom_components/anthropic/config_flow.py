"""Config flow for Anthropic integration."""
from __future__ import annotations

import logging
import aiohttp
import asyncio
from typing import Any, Dict, Optional

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY, CONF_LLM_HASS_API
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import llm
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    TemplateSelector,
)

from .const import (
    ANTHROPIC_MODELS,
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

_LOGGER = logging.getLogger(__name__)


# Define our own APIError class for compatibility
class APIError(Exception):
    """API Error."""

    def __init__(self, message, type, status_code):
        """Initialize the error."""
        self.message = message
        self.type = type
        self.status_code = status_code
        super().__init__(message)


async def validate_api_key(hass: HomeAssistant, api_key: str) -> None:
    """Validate the API key by making a request."""
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    data = {
        "model": AnthropicModels.default(),
        "max_tokens": 10,
        "system": "You are Claude, a helpful AI assistant.",
        "messages": [{"role": "user", "content": "Hello"}],
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with asyncio.timeout(10):
                async with session.post(url, headers=headers, json=data) as response:
                    if response.status != 200:
                        error_data = await response.text()
                        try:
                            error_json = await response.json()
                            if "error" in error_json:
                                error_data = error_json["error"].get("message", error_data)
                        except:
                            pass
                        
                        raise APIError(
                            message=f"API request failed: {error_data}",
                            type="api_error",
                            status_code=response.status,
                        )
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


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Anthropic."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({vol.Required(CONF_API_KEY): str}),
            )

        errors = {}

        try:
            await validate_api_key(self.hass, user_input[CONF_API_KEY])
        except APIError as err:
            _LOGGER.error("API error: %s", err)
            errors["base"] = "invalid_auth"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected error")
            errors["base"] = "unknown"
        else:
            return self.async_create_entry(title="Anthropic", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_API_KEY): str}),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlow(config_entry)


class OptionsFlow(config_entries.OptionsFlow):
    """Anthropic config flow options handler."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            # Update the API key if provided
            if CONF_API_KEY in user_input and user_input[CONF_API_KEY]:
                try:
                    # Validate the new API key
                    await validate_api_key(self.hass, user_input[CONF_API_KEY])
                    # Update the config entry with the new API key
                    new_data = {**self._config_entry.data, CONF_API_KEY: user_input[CONF_API_KEY]}
                    self.hass.config_entries.async_update_entry(self._config_entry, data=new_data)
                except Exception as err:
                    _LOGGER.error("Error validating new API key: %s", err)
                    return self.async_show_form(
                        step_id="init",
                        data_schema=vol.Schema(self._get_options_schema()),
                        errors={"base": "invalid_auth"},
                    )
                
                # Remove API key from options to avoid storing it twice
                user_input.pop(CONF_API_KEY)
            
            # Handle "none" value for LLM_HASS_API
            if CONF_LLM_HASS_API in user_input and user_input[CONF_LLM_HASS_API] == "none":
                user_input.pop(CONF_LLM_HASS_API)
            
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(self._get_options_schema()),
        )
    
    def _get_options_schema(self) -> dict:
        """Get the options schema."""
        options = {
            vol.Optional(
                CONF_API_KEY,
                default="",
                description="Leave empty to keep the current API key",
            ): str,
            vol.Optional(
                CONF_PROMPT,
                default=self._config_entry.options.get(CONF_PROMPT, DEFAULT_PROMPT),
            ): TemplateSelector(),
            vol.Optional(
                CONF_CONTROL_HA,
                default=self._config_entry.options.get(CONF_CONTROL_HA, DEFAULT_CONTROL_HA),
            ): bool,
        }
        
        # Add LLM API selector if control_ha is enabled
        if self._config_entry.options.get(CONF_CONTROL_HA, DEFAULT_CONTROL_HA):
            # Get available LLM APIs
            hass_apis = [
                # "No control" means the model will not have access to Home Assistant devices
                # and will not be able to control them or get information about their state
                {"label": "No control", "value": "none"}
            ]
            
            for api in llm.async_get_apis(self.hass):
                # "Assist" and other APIs allow the model to control Home Assistant devices
                # and get information about their state through tools
                hass_apis.append({
                    "label": api.name,  # Usually "Assist" for the standard Home Assistant API
                    "value": api.id,    # Usually "assist" for the standard API
                })
            
            options[vol.Optional(
                CONF_LLM_HASS_API,
                description={"suggested_value": self._config_entry.options.get(CONF_LLM_HASS_API)},
                default="none",
            )] = vol.In({api["value"]: api["label"] for api in hass_apis})
        
        options[vol.Optional(
            CONF_RECOMMENDED_SETTINGS,
            default=self._config_entry.options.get(
                CONF_RECOMMENDED_SETTINGS, DEFAULT_RECOMMENDED_SETTINGS
            ),
        )] = bool

        # Always add advanced options to the schema
        # They will only be visible in the UI when recommended settings are disabled
        options.update(
            {
                vol.Optional(
                    CONF_CHAT_MODEL,
                    default=self._config_entry.options.get(
                        CONF_CHAT_MODEL, AnthropicModels.default()
                    ),
                ): vol.In({model: model for model in ANTHROPIC_MODELS}),
                vol.Optional(
                    CONF_MAX_TOKENS,
                    default=self._config_entry.options.get(
                        CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS
                    ),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=1,
                        max=4096,
                        step=1,
                        mode="box",
                    )
                ),
                vol.Optional(
                    CONF_TEMPERATURE,
                    default=self._config_entry.options.get(
                        CONF_TEMPERATURE, DEFAULT_TEMPERATURE
                    ),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=0.0,
                        max=1.0,
                        step=0.05,
                        mode="slider",
                    )
                ),
            }
        )
        
        return options