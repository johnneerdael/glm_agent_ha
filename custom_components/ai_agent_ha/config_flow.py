"""Config flow for AI Agent HA integration."""
from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
    TextSelectorConfig,
)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PROVIDERS = {
    "llama": "Llama",
    "openai": "OpenAI",
    "gemini": "Google Gemini",
    "openrouter": "OpenRouter",
    "anthropic": "Anthropic (Claude)",
}

TOKEN_FIELD_NAMES = {
    "llama": "llama_token",
    "openai": "openai_token",
    "gemini": "gemini_token",
    "openrouter": "openrouter_token",
    "anthropic": "anthropic_token",
}

TOKEN_LABELS = {
    "llama": "Llama API Token",
    "openai": "OpenAI API Key",
    "gemini": "Google Gemini API Key",
    "openrouter": "OpenRouter API Key",
    "anthropic": "Anthropic API Key",
}

DEFAULT_MODELS = {
    "llama": "Llama-4-Maverick-17B-128E-Instruct-FP8",
    "openai": "gpt-3.5-turbo",
    "gemini": "gemini-1.5-flash",
    "openrouter": "openai/gpt-4o",
    "anthropic": "claude-3-5-sonnet-20241022",
}

AVAILABLE_MODELS = {
    "openai": [
        "gpt-3.5-turbo",
        "gpt-4",
        "gpt-4-turbo",
        "gpt-4o",
        "gpt-4o-mini",
        "o1-preview",
        "o1-mini",
    ],
    "gemini": [
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "gemini-1.0-pro",
        "gemini-2.0-flash-exp",
    ],
    "openrouter": [
        "openai/gpt-4o",
        "openai/gpt-4-turbo",
        "openai/gpt-3.5-turbo",
        "anthropic/claude-3.5-sonnet",
        "anthropic/claude-3-sonnet",
        "anthropic/claude-3-haiku",
        "meta-llama/llama-3.1-70b-instruct",
        "meta-llama/llama-3.2-90b-instruct",
        "google/gemini-pro",
        "mistralai/mixtral-8x7b-instruct",
        "deepseek/deepseek-r1",
    ],
    "anthropic": [
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
    ],
    "llama": [
        "Llama-4-Maverick-17B-128E-Instruct-FP8",
        "Llama-3.1-70B-Instruct",
        "Llama-3.1-8B-Instruct",
        "Llama-3.2-90B-Instruct",
    ],
}

DEFAULT_PROVIDER = "openai"

class AiAgentHaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for AI Agent HA."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Check if this provider is already configured
            await self.async_set_unique_id(f"ai_agent_ha_{user_input['ai_provider']}")
            self._abort_if_unique_id_configured()

            self.config_data = {"ai_provider": user_input["ai_provider"]}
            return await self.async_step_configure()

        # Show provider selection form
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("ai_provider"): SelectSelector(
                    SelectSelectorConfig(
                        options=[{"value": k, "label": v} for k, v in PROVIDERS.items()]
                    )
                ),
            })
        )

    async def async_step_configure(self, user_input=None):
        """Handle the configuration step for the selected provider."""
        errors = {}
        provider = self.config_data["ai_provider"]
        token_field = TOKEN_FIELD_NAMES[provider]
        token_label = TOKEN_LABELS[provider]
        default_model = DEFAULT_MODELS[provider]
        available_models = AVAILABLE_MODELS.get(provider, [default_model])
        
        if user_input is not None:
            try:
                # Validate the token
                token_value = user_input.get(token_field)
                if not token_value:
                    errors[token_field] = "required"
                    raise InvalidApiKey
                
                # Store the configuration data
                self.config_data[token_field] = token_value
                
                # Add model configuration if provided
                selected_model = user_input.get("model")
                custom_model = user_input.get("custom_model")
                
                if custom_model:
                    # Use custom model if provided
                    self.config_data["models"] = {
                        provider: custom_model
                    }
                elif selected_model and selected_model != "Custom...":
                    # Use selected model if it's not the "Custom..." option
                    self.config_data["models"] = {
                        provider: selected_model
                    }
                
                return self.async_create_entry(
                    title=f"AI Agent HA ({PROVIDERS[provider]})",
                    data=self.config_data,
                )
            except InvalidApiKey:
                errors["base"] = "invalid_api_key"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        # Build schema for the selected provider
        schema_dict = {
            vol.Required(token_field): TextSelector(
                TextSelectorConfig(type="password")
            ),
        }
        
        # Add model selection if available
        if available_models:
            # Add predefined models + custom option
            model_options = available_models + ["Custom..."]
            schema_dict[vol.Optional("model", default=default_model)] = SelectSelector(
                SelectSelectorConfig(options=model_options)
            )
            schema_dict[vol.Optional("custom_model")] = TextSelector(
                TextSelectorConfig(type="text")
            )

        return self.async_show_form(
            step_id="configure",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
            description_placeholders={
                "token_label": token_label,
                "provider": PROVIDERS[provider],
            }
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return AiAgentHaOptionsFlowHandler()

class InvalidApiKey(HomeAssistantError):
    """Error to indicate there is an invalid API key."""

class AiAgentHaOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for AI Agent HA."""
    
    def __init__(self):
        """Initialize options flow."""
        self.options_data = {}

    async def async_step_init(self, user_input=None):
        """Handle the initial options step - provider selection."""
        current_provider = self.config_entry.data.get("ai_provider", DEFAULT_PROVIDER)
        
        if user_input is not None:
            # Store selected provider and move to configure step
            self.options_data = {
                "ai_provider": user_input["ai_provider"],
                "current_provider": current_provider
            }
            return await self.async_step_configure_options()

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required("ai_provider", default=current_provider): SelectSelector(
                    SelectSelectorConfig(
                        options=[{"value": k, "label": v} for k, v in PROVIDERS.items()]
                    )
                ),
            }),
            description_placeholders={
                "current_provider": PROVIDERS[current_provider]
            }
        )

    async def async_step_configure_options(self, user_input=None):
        """Handle the configuration step for the selected provider in options."""
        errors = {}
        provider = self.options_data["ai_provider"]
        current_provider = self.options_data["current_provider"]
        token_field = TOKEN_FIELD_NAMES[provider]
        token_label = TOKEN_LABELS[provider]
        
        # Get current configuration
        current_models = self.config_entry.data.get("models", {})
        current_model = current_models.get(provider, DEFAULT_MODELS[provider])
        current_token = self.config_entry.data.get(token_field, "")
        available_models = AVAILABLE_MODELS.get(provider, [DEFAULT_MODELS[provider]])
        
        # Use current token if provider hasn't changed, otherwise empty
        display_token = current_token if provider == current_provider else ""
        
        if user_input is not None:
            try:
                token_value = user_input.get(token_field)
                if not token_value:
                    errors[token_field] = "required"
                else:
                    # Prepare the updated configuration
                    updated_data = dict(self.config_entry.data)
                    updated_data["ai_provider"] = provider
                    updated_data[token_field] = token_value
                    
                    # Update model configuration
                    selected_model = user_input.get("model")
                    custom_model = user_input.get("custom_model")
                    
                    if custom_model:
                        # Use custom model if provided
                        if "models" not in updated_data:
                            updated_data["models"] = {}
                        updated_data["models"][provider] = custom_model
                    elif selected_model and selected_model != "Custom...":
                        # Use selected model if it's not the "Custom..." option
                        if "models" not in updated_data:
                            updated_data["models"] = {}
                        updated_data["models"][provider] = selected_model
                    
                    # Update the config entry
                    self.hass.config_entries.async_update_entry(
                        self.config_entry, data=updated_data
                    )
                    
                    return self.async_create_entry(title="", data={})
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception in options flow")
                errors["base"] = "unknown"

        # Build schema for the selected provider
        schema_dict = {
            vol.Required(token_field, default=display_token): TextSelector(
                TextSelectorConfig(type="password")
            ),
        }
        
        # Add model selection if available
        if available_models:
            # Add predefined models + custom option
            model_options = available_models + ["Custom..."]
            schema_dict[vol.Optional("model", default=current_model)] = SelectSelector(
                SelectSelectorConfig(options=model_options)
            )
            schema_dict[vol.Optional("custom_model")] = TextSelector(
                TextSelectorConfig(type="text")
            )

        return self.async_show_form(
            step_id="configure_options",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
            description_placeholders={
                "token_label": token_label,
                "provider": PROVIDERS[provider],
            }
        )