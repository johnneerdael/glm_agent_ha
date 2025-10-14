"""Config flow for GLM Coding Plan Agent HA integration."""

from __future__ import annotations

__all__ = ["AiAgentHaConfigFlow"]

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

PROVIDERS = {
    "openai": "GLM Coding Plan API",
}

TOKEN_FIELD_NAMES = {
    "openai": "openai_token",
}

TOKEN_LABELS = {
    "openai": "GLM Coding Plan API Key",
}

DEFAULT_MODELS = {
    "openai": "GLM-4.6",
}

DEFAULT_PROVIDER = "openai"

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
            # Check if this provider is already configured
            await self.async_set_unique_id(f"glm_agent_ha_{user_input['ai_provider']}")
            self._abort_if_unique_id_configured()

            self.config_data = {
                "ai_provider": user_input["ai_provider"],
                "plan": user_input.get("plan", DEFAULT_PLAN)
            }
            return await self.async_step_configure()

        # Show provider and plan selection form
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("ai_provider"): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                {"value": k, "label": v} for k, v in PROVIDERS.items()
                            ]
                        )
                    ),
                    vol.Required("plan", default=DEFAULT_PLAN): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                {"value": k, "label": v} for k, v in PLANS.items()
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
                )
            }
        )

    async def async_step_configure(self, user_input=None):
        """Handle the configuration step for the selected provider."""
        errors = {}
        provider = self.config_data["ai_provider"]
        plan = self.config_data.get("plan", DEFAULT_PLAN)
        token_field = TOKEN_FIELD_NAMES[provider]
        token_label = TOKEN_LABELS[provider]
        default_model = DEFAULT_MODELS[provider]
        # Use default model for the provider (simplified approach)
        available_models = [default_model]
        plan_capabilities = PLAN_CAPABILITIES.get(plan, {})

        if user_input is not None:
            try:
                # Validate the token
                token_value = user_input.get(token_field)
                if not token_value:
                    errors[token_field] = "required"
                elif len(token_value.strip()) < 10:
                    errors[token_field] = "invalid_api_key"
                else:
                    # Store the configuration data
                    self.config_data[token_field] = token_value

                    # Use default model for the provider (simplified approach)
                    self.config_data["models"] = {provider: default_model}

                    _LOGGER.debug(
                        f"Config flow - Provider: {provider}, Plan: {plan}, Model: {default_model}"
                    )

                    # Store plan capabilities
                    self.config_data["plan_capabilities"] = plan_capabilities
                    self.config_data["mcp_servers"] = plan_capabilities.get("mcp_servers", [])
                    self.config_data["features"] = plan_capabilities.get("features", [])

                    return self.async_create_entry(
                        title=f"GLM Coding Plan Agent HA ({PROVIDERS[provider]} - {PLANS[plan]})",
                        data=self.config_data,
                    )
            except Exception as e:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception in config flow: %s", e)
                errors["base"] = "unknown"

        # Build schema for providers (simplified - just token)
        schema_dict = {
            vol.Required(token_field): TextSelector(
                TextSelectorConfig(type="password")
            ),
        }

        return self.async_show_form(
            step_id="configure",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
            description_placeholders={
                "token_label": token_label,
                "provider": PROVIDERS[provider],
                "plan": PLANS[plan],
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
        """Handle the initial options step - provider selection."""
        current_provider = self.config_entry.data.get("ai_provider", DEFAULT_PROVIDER)

        if user_input is not None:
            # Store selected provider and move to configure step
            self.options_data = {
                "ai_provider": user_input["ai_provider"],
                "current_provider": current_provider,
            }
            return await self.async_step_configure_options()

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "ai_provider", default=current_provider
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                {"value": k, "label": v} for k, v in PROVIDERS.items()
                            ]
                        )
                    ),
                }
            ),
            description_placeholders={"current_provider": PROVIDERS[current_provider]},
        )

    async def async_step_configure_options(self, user_input=None):
        """Handle the configuration step for the selected provider in options."""
        errors = {}
        provider = self.options_data["ai_provider"]
        current_provider = self.options_data["current_provider"]
        token_field = TOKEN_FIELD_NAMES[provider]
        token_label = TOKEN_LABELS[provider]

        # Get current configuration
        current_token = self.config_entry.data.get(token_field, "")

        # Use current token if provider hasn't changed, otherwise empty
        display_token = current_token if provider == current_provider else ""

        if user_input is not None:
            try:
                token_value = user_input.get(token_field)
                if not token_value:
                    errors[token_field] = "required"
                elif len(token_value.strip()) < 10:
                    errors[token_field] = "invalid_api_key"
                else:
                    # Prepare the updated configuration
                    updated_data = dict(self.config_entry.data)
                    updated_data["ai_provider"] = provider
                    updated_data[token_field] = token_value

                    # Use default model for the provider (simplified approach)
                    updated_data["models"] = {provider: DEFAULT_MODELS[provider]}

                    _LOGGER.debug(
                        f"Options flow - Updated config for {provider} with default model: {DEFAULT_MODELS[provider]}"
                    )

                    # Update the config entry
                    self.hass.config_entries.async_update_entry(
                        self.config_entry, data=updated_data
                    )

                    return self.async_create_entry(title="", data={})
            except Exception as e:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception in options flow: %s", e)
                errors["base"] = "unknown"

        # Build schema for providers (simplified - just token)
        schema_dict = {
            vol.Required(token_field, default=display_token): TextSelector(
                TextSelectorConfig(type="password")
            ),
        }

        return self.async_show_form(
            step_id="configure_options",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
            description_placeholders={
                "token_label": token_label,
                "provider": PROVIDERS[provider],
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
