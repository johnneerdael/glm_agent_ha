"""Config flow for Llama Query integration."""
from __future__ import annotations

import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    EntitySelector,
    EntitySelectorConfig,
)

from .const import DOMAIN, CONF_API_KEY, CONF_WEATHER_ENTITY

_LOGGER = logging.getLogger(__name__)

class LlamaQueryConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Llama Query."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            try:
                # Validate the API key by making a test request
                # You might want to add actual validation here
                if not user_input[CONF_API_KEY].strip():
                    raise InvalidApiKey

                return self.async_create_entry(
                    title="Llama Query",
                    data={
                        CONF_API_KEY: user_input[CONF_API_KEY],
                        CONF_WEATHER_ENTITY: user_input.get(CONF_WEATHER_ENTITY),
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
                vol.Required(CONF_API_KEY): TextSelector(
                    TextSelectorConfig(type="password")
                ),
                vol.Optional(CONF_WEATHER_ENTITY): EntitySelector(
                    EntitySelectorConfig(domain="weather")
                ),
            }),
            errors=errors,
        )

class InvalidApiKey(HomeAssistantError):
    """Error to indicate there is an invalid API key.""" 