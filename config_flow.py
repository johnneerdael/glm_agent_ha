"""Config flow for Llama Query integration."""
from __future__ import annotations

import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    EntitySelector,
    EntitySelectorConfig,
)
from homeassistant.const import CONF_NAME

from .const import DOMAIN, CONF_API_KEY, CONF_WEATHER_ENTITY

_LOGGER = logging.getLogger(__name__)

PROVIDERS = {
    "llama": "Llama",
    "openai": "OpenAI",
}

TOKEN_NAMES = {
    "llama": "Llama API Key",
    "openai": "OpenAI API Key",
}

DEFAULT_PROVIDER = "llama"

class AiAgentHaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Llama Query."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        provider = user_input.get("ai_provider") if user_input else DEFAULT_PROVIDER
        token_label = TOKEN_NAMES.get(provider, "API Token")

        if user_input is not None:
            try:
                # Validate the API key by making a test request
                # You might want to add actual validation here
                if not user_input.get("llm_token"):
                    raise InvalidApiKey

                return self.async_create_entry(
                    title=f"AI Agent HA ({PROVIDERS.get(user_input['ai_provider'], user_input['ai_provider'])})",
                    data={
                        "ai_provider": user_input["ai_provider"],
                        "llm_token": user_input["llm_token"]
                    },
                )
            except InvalidApiKey:
                errors["base"] = "invalid_api_key"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("ai_provider", default=provider): vol.In(list(PROVIDERS.keys())),
                vol.Required("llm_token"): str,
            }),
            errors=errors,
            description_placeholders={
                "token_label": token_label
            }
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return AiAgentHaOptionsFlowHandler()

class InvalidApiKey(HomeAssistantError):
    """Error to indicate there is an invalid API key."""

class AiAgentHaOptionsFlowHandler(config_entries.OptionsFlow):
    pass

    async def async_step_init(self, user_input=None):
        errors = {}
        provider = user_input.get("ai_provider") if user_input else self.config_entry.data.get("ai_provider", DEFAULT_PROVIDER)
        token_label = TOKEN_NAMES.get(provider, "API Token")
        default_token = user_input.get("llm_token") if user_input else self.config_entry.data.get("llm_token", "")

        if user_input is not None:
            if not user_input.get("llm_token"):
                errors["llm_token"] = "required"
            if not errors:
                return self.async_create_entry(
                    title="",
                    data={
                        "ai_provider": user_input["ai_provider"],
                        "llm_token": user_input["llm_token"]
                    }
                )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required("ai_provider", default=provider): vol.In(list(PROVIDERS.keys())),
                vol.Required("llm_token", default=default_token): str,
            }),
            errors=errors,
            description_placeholders={
                "token_label": token_label
            }
        ) 