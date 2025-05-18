"""Config flow for Llama Query integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
import aiohttp

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("api_key"): str,
    }
)

async def validate_api_key(hass: HomeAssistant, api_key: str) -> bool:
    """Validate the API key by making a test request."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            # Make a minimal test request
            async with session.post(
                "https://api.llama.com/v1/chat/completions",
                headers=headers,
                json={
                    "model": "Llama-4-Maverick-17B-128E-Instruct-FP8",
                    "messages": [{"role": "user", "content": "test"}],
                    "max_tokens": 1
                }
            ) as response:
                if response.status == 200:
                    return True
                _LOGGER.error(f"API validation failed with status {response.status}")
                return False
        except Exception as e:
            _LOGGER.error(f"API validation failed: {str(e)}")
            return False

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Llama Query."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Validate the API key
                if await validate_api_key(self.hass, user_input["api_key"]):
                    return self.async_create_entry(
                        title="Llama Query",
                        data=user_input
                    )
                else:
                    errors["base"] = "invalid_api_key"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        ) 