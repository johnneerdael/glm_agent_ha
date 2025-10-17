"""Config flow for GLM Coding Plan Agent HA integration."""

from __future__ import annotations

__all__ = ["AiAgentHaConfigFlow"]

import logging
from typing import Dict, Optional

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


def _validate_and_prepare_description_placeholders(
    placeholders: Dict[str, str],
    fallback_values: Optional[Dict[str, str]] = None
) -> Dict[str, str]:
    """Validate and prepare description placeholders with fallback values."""
    if fallback_values is None:
        fallback_values = {}

    validated_placeholders = {}
    missing_variables = []

    for key, value in placeholders.items():
        if value is None or value == "":
            if key in fallback_values:
                validated_placeholders[key] = fallback_values[key]
                _LOGGER.warning("Translation variable '%s' was missing, using fallback: %s", key, fallback_values[key])
            else:
                validated_placeholders[key] = f"[{key.upper()}]"
                missing_variables.append(key)
                _LOGGER.error("Translation variable '%s' is missing and no fallback provided", key)
        else:
            validated_placeholders[key] = value

    if missing_variables:
        _LOGGER.warning("Missing translation variables: %s", ", ".join(missing_variables))

    return validated_placeholders

from .const import (
    CONF_CACHE_TTL,
    CONF_ENABLE_AREA_TOPOLOGY,
    CONF_ENABLE_DIAGNOSTICS,
    CONF_ENABLE_ENERGY,
    CONF_ENABLE_ENTITY_RELATIONSHIPS,
    CONF_ENABLE_ENTITY_TYPE_CACHE,
    DEFAULT_CACHE_TTL,
    DOMAIN,
    CONF_PLAN,
)

_LOGGER = logging.getLogger(__name__)

# Simplified since we only support one provider
PROVIDER_NAME = "GLM Coding Plan API"
TOKEN_FIELD = "openai_token"
TOKEN_LABEL = "GLM Coding Plan API Key"

# Available GLM models
GLM_MODELS = {
    "GLM-4.6": "GLM-4.6 (Latest, most capable)",
    "GLM-4.5": "GLM-4.5 (Balanced performance)",
    "GLM-4.5-air": "GLM-4.5-air (Fast)",
}

DEFAULT_MODEL = "GLM-4.6"

# Plan definitions
PLANS = {
    "lite": "GLM Coding Lite",
    "pro": "GLM Coding Pro",
    "max": "GLM Coding Max",
}

DEFAULT_PLAN = "lite"

# Plan capabilities
PLAN_CAPABILITIES = {
    "lite": {
        "mcp_servers": [],
        "features": ["basic_chat"]
    },
    "pro": {
        "mcp_servers": ["zai-mcp-server", "web-search-prime"],
        "features": ["basic_chat", "image_analysis", "web_search"]
    },
    "max": {
        "mcp_servers": ["zai-mcp-server", "web-search-prime"],
        "features": ["basic_chat", "image_analysis", "web_search", "advanced_features"]
    }
}


class AiAgentHaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg,misc]
    """Handle a config flow for GLM Coding Plan Agent HA."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL
    
    # Add explicit domain attribute for debugging
    DOMAIN = DOMAIN

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        _LOGGER.debug("Creating options flow for config entry: %s", config_entry.entry_id)
        try:
            return AiAgentHaOptionsFlowHandler(config_entry)
        except Exception as e:
            _LOGGER.error("Error creating options flow: %s", e)
            return None

    def __init__(self):
        """Initialize the config flow."""
        super().__init__()
        self.config_data = {}
        _LOGGER.debug("AiAgentHaConfigFlow initialized with domain: %s", self.DOMAIN)

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Set unique ID since we only have one provider
            await self.async_set_unique_id("glm_agent_ha_openai")
            self._abort_if_unique_id_configured()

            self.config_data = {
                "plan": user_input.get("plan", DEFAULT_PLAN),
                "model": user_input.get("model", DEFAULT_MODEL),
                "ai_provider": "openai"  # Fixed provider
            }
            return await self.async_step_configure()

        # Show plan and model selection form (no provider selection)
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("plan", default=DEFAULT_PLAN): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                {"value": k, "label": v} for k, v in PLANS.items()
                            ]
                        )
                    ),
                    vol.Required("model", default=DEFAULT_MODEL): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                {"value": k, "label": v} for k, v in GLM_MODELS.items()
                            ]
                        )
                    ),
                }
            ),
            description_placeholders={
                "plan_descriptions": (
                    "Lite: Basic chat functionality\n"
                    "Pro: Chat + Image analysis + Web search\n"
                    "Max: All Pro features + Advanced capabilities"
                ),
                "model_descriptions": (
                    "GLM-4.6: Latest model with best performance\n"
                    "GLM-4.5: Balanced model for most tasks\n"
                    "GLM-4.5-air: Fast responses for real-time applications"
                )
            }
        )

    async def async_step_configure(self, user_input=None):
        """Handle the API key configuration step."""
        errors = {}
        plan = self.config_data.get("plan", DEFAULT_PLAN)
        model = self.config_data.get("model", DEFAULT_MODEL)
        plan_capabilities = PLAN_CAPABILITIES.get(plan, {})

        if user_input is not None:
            try:
                # Validate the token
                token_value = user_input.get(TOKEN_FIELD)
                if not token_value:
                    errors[TOKEN_FIELD] = "required"
                elif len(token_value.strip()) < 10:
                    errors[TOKEN_FIELD] = "invalid_api_key"
                else:
                    # Store the configuration data
                    self.config_data[TOKEN_FIELD] = token_value
                    self.config_data["models"] = {"openai": model}

                    _LOGGER.debug(
                        f"Config flow - Plan: {plan}, Model: {model}"
                    )

                    # Store plan capabilities
                    self.config_data["plan_capabilities"] = plan_capabilities
                    self.config_data["mcp_servers"] = plan_capabilities.get("mcp_servers", [])
                    self.config_data["features"] = plan_capabilities.get("features", [])

                    return self.async_create_entry(
                        title=f"GLM Coding Plan Agent HA ({PLANS[plan]} - {model})",
                        data=self.config_data,
                    )
            except Exception as e:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception in config flow: %s", e)
                errors["base"] = "unknown"

        # Build schema for API key
        schema_dict = {
            vol.Required(TOKEN_FIELD): TextSelector(
                TextSelectorConfig(type="password")
            ),
        }

        return self.async_show_form(
            step_id="configure",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
            description_placeholders={
                "token_label": TOKEN_LABEL,
                "provider": PROVIDER_NAME,
                "plan": PLANS[plan],
                "model": model,
                "plan_features": ", ".join(plan_capabilities.get("features", [])),
                "mcp_servers": ", ".join(plan_capabilities.get("mcp_servers", [])) or "None",
            },
        )


class InvalidApiKey(HomeAssistantError):
    """Error to indicate there is an invalid API key."""


class AiAgentHaOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for GLM Coding Plan Agent HA."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry
        self.options_data = {}

    async def async_step_init(self, user_input=None):
        """Handle the initial options step - choose what to configure."""
        if user_input is not None:
            action = user_input["action"]
            if action == "model":
                return await self.async_step_model()
            elif action == "api_key":
                return await self.async_step_api_key()
            elif action == "advanced":
                return await self.async_step_advanced()

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required("action", default="model"): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                {"value": "model", "label": "Change AI Model"},
                                {"value": "api_key", "label": "Update API Key"},
                                {"value": "advanced", "label": "Advanced Settings"},
                            ]
                        )
                    ),
                }
            ),
            description_placeholders=_validate_and_prepare_description_placeholders(
                {
                    "current_provider": PROVIDER_NAME,
                    "current_model": GLM_MODELS.get(
                        self.config_entry.data.get("models", {}).get("openai", DEFAULT_MODEL),
                        self.config_entry.data.get("models", {}).get("openai", DEFAULT_MODEL)
                    )
                },
                fallback_values={
                    "current_provider": "GLM Coding Plan API",
                    "current_model": DEFAULT_MODEL
                }
            ),
        )

    async def async_step_model(self, user_input=None):
        """Handle model selection step."""
        current_model = self.config_entry.data.get("models", {}).get("openai", DEFAULT_MODEL)

        if user_input is not None:
            # Prepare the updated configuration
            updated_data = dict(self.config_entry.data)
            updated_data["models"] = {"openai": user_input["model"]}

            _LOGGER.debug(f"Options flow - Updated model to: {user_input['model']}")

            # Update the config entry
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=updated_data
            )

            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="model",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "model", default=current_model
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                {"value": k, "label": v} for k, v in GLM_MODELS.items()
                            ]
                        )
                    ),
                }
            ),
            description_placeholders=_validate_and_prepare_description_placeholders(
                {
                    "current_model": GLM_MODELS.get(current_model, current_model),
                    "model_descriptions": (
                        "GLM-4.6: Latest model with best performance\n"
                        "GLM-4.5: Balanced model for most tasks\n"
                        "GLM-4.5-air: Fast responses for real-time applications"
                    )
                },
                fallback_values={
                    "current_model": DEFAULT_MODEL,
                    "model_descriptions": "GLM-4.6: Latest model with best performance"
                }
            ),
        )

    async def async_step_api_key(self, user_input=None):
        """Handle API key update step."""
        current_model = self.config_entry.data.get("models", {}).get("openai", DEFAULT_MODEL)
        current_token = self.config_entry.data.get(TOKEN_FIELD, "")

        if user_input is not None:
            try:
                token_value = user_input.get(TOKEN_FIELD)
                if not token_value:
                    errors = {"api_key": "required"}
                elif len(token_value.strip()) < 10:
                    errors = {"api_key": "invalid_api_key"}
                else:
                    # Prepare the updated configuration
                    updated_data = dict(self.config_entry.data)
                    updated_data[TOKEN_FIELD] = token_value

                    _LOGGER.debug("Options flow - Updated API key")

                    # Update the config entry
                    self.hass.config_entries.async_update_entry(
                        self.config_entry, data=updated_data
                    )

                    return self.async_create_entry(title="", data={})
            except Exception as e:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception in options flow: %s", e)
                errors = {"base": "unknown"}

        # Build schema for API key
        schema_dict = {
            vol.Required(TOKEN_FIELD, default=current_token): TextSelector(
                TextSelectorConfig(type="password")
            ),
        }

        return self.async_show_form(
            step_id="api_key",
            data_schema=vol.Schema(schema_dict),
            errors=errors if 'errors' in locals() else {},
            description_placeholders={
                "token_label": TOKEN_LABEL,
                "provider": PROVIDER_NAME,
                "model": GLM_MODELS.get(current_model, current_model),
            },
        )

    async def async_step_advanced(self, user_input=None):
        """Handle advanced settings step."""
        # Forward to the existing advanced options method
        return await self.async_step_advanced_options(user_input)

    async def async_step_configure_options(self, user_input=None):
        """Handle the API key configuration step in options."""
        errors = {}
        model = self.options_data["model"]
        current_model = self.options_data["current_model"]

        # Get current configuration
        current_token = self.config_entry.data.get(TOKEN_FIELD, "")

        if user_input is not None:
            try:
                token_value = user_input.get(TOKEN_FIELD)
                if not token_value:
                    errors[TOKEN_FIELD] = "required"
                elif len(token_value.strip()) < 10:
                    errors[TOKEN_FIELD] = "invalid_api_key"
                else:
                    # Prepare the updated configuration
                    updated_data = dict(self.config_entry.data)
                    updated_data[TOKEN_FIELD] = token_value
                    updated_data["models"] = {"openai": model}

                    _LOGGER.debug(
                        f"Options flow - Updated config with model: {model}"
                    )

                    # Update the config entry
                    self.hass.config_entries.async_update_entry(
                        self.config_entry, data=updated_data
                    )

                    return self.async_create_entry(title="", data={})
            except Exception as e:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception in options flow: %s", e)
                errors["base"] = "unknown"

        # Build schema for API key
        schema_dict = {
            vol.Required(TOKEN_FIELD, default=current_token): TextSelector(
                TextSelectorConfig(type="password")
            ),
        }

        return self.async_show_form(
            step_id="configure_options",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
            description_placeholders={
                "token_label": TOKEN_LABEL,
                "provider": PROVIDER_NAME,
                "model": GLM_MODELS.get(model, model),
            },
        )

    async def async_step_advanced_options(self, user_input=None):
        """Handle advanced options for context features."""
        errors = {}
        
        # Get current values
        current_cache_ttl = self.config_entry.options.get(CONF_CACHE_TTL, DEFAULT_CACHE_TTL)
        current_enable_diagnostics = self.config_entry.options.get(CONF_ENABLE_DIAGNOSTICS, True)
        current_enable_energy = self.config_entry.options.get(CONF_ENABLE_ENERGY, True)
        current_enable_area_topology = self.config_entry.options.get(CONF_ENABLE_AREA_TOPOLOGY, True)
        current_enable_entity_type_cache = self.config_entry.options.get(CONF_ENABLE_ENTITY_TYPE_CACHE, True)
        current_enable_entity_relationships = self.config_entry.options.get(CONF_ENABLE_ENTITY_RELATIONSHIPS, True)
        
        if user_input is not None:
            try:
                updated_options = dict(self.config_entry.options)
                
                # Update cache TTL
                cache_ttl = user_input.get(CONF_CACHE_TTL, current_cache_ttl)
                if cache_ttl < 60:  # Minimum 1 minute
                    errors[CONF_CACHE_TTL] = "min_60_seconds"
                elif cache_ttl > 3600:  # Maximum 1 hour
                    errors[CONF_CACHE_TTL] = "max_3600_seconds"
                else:
                    updated_options[CONF_CACHE_TTL] = cache_ttl
                
                # Update feature toggles
                updated_options[CONF_ENABLE_DIAGNOSTICS] = user_input.get(
                    CONF_ENABLE_DIAGNOSTICS, current_enable_diagnostics
                )
                updated_options[CONF_ENABLE_ENERGY] = user_input.get(
                    CONF_ENABLE_ENERGY, current_enable_energy
                )
                updated_options[CONF_ENABLE_AREA_TOPOLOGY] = user_input.get(
                    CONF_ENABLE_AREA_TOPOLOGY, current_enable_area_topology
                )
                updated_options[CONF_ENABLE_ENTITY_TYPE_CACHE] = user_input.get(
                    CONF_ENABLE_ENTITY_TYPE_CACHE, current_enable_entity_type_cache
                )
                updated_options[CONF_ENABLE_ENTITY_RELATIONSHIPS] = user_input.get(
                    CONF_ENABLE_ENTITY_RELATIONSHIPS, current_enable_entity_relationships
                )
                
                # Update the config entry options
                self.hass.config_entries.async_update_entry(
                    self.config_entry, options=updated_options
                )
                
                return self.async_create_entry(title="", data={})
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception in advanced options flow")
                errors["base"] = "unknown"
        
        return self.async_show_form(
            step_id="advanced_options",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_CACHE_TTL,
                    default=current_cache_ttl
                ): vol.All(vol.Coerce(int), vol.Range(min=60, max=3600)),
                vol.Optional(
                    CONF_ENABLE_DIAGNOSTICS,
                    default=current_enable_diagnostics
                ): bool,
                vol.Optional(
                    CONF_ENABLE_ENERGY,
                    default=current_enable_energy
                ): bool,
                vol.Optional(
                    CONF_ENABLE_AREA_TOPOLOGY,
                    default=current_enable_area_topology
                ): bool,
                vol.Optional(
                    CONF_ENABLE_ENTITY_TYPE_CACHE,
                    default=current_enable_entity_type_cache
                ): bool,
                vol.Optional(
                    CONF_ENABLE_ENTITY_RELATIONSHIPS,
                    default=current_enable_entity_relationships
                ): bool,
            }),
            errors=errors,
        )
