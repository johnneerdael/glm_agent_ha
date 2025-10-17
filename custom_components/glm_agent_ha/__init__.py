"""The GLM Coding Plan Agent HA integration."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from types import SimpleNamespace
from typing import Dict, List, Optional, Set

import voluptuous as vol
from homeassistant.components.frontend import async_register_built_in_panel
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

# Define platforms for proper Home Assistant integration
PLATFORMS = ["conversation", "ai_task"]

from .agent import AiAgentHaAgent
from .const import (
    DOMAIN,
)
from .debug_service import GLMAgentDebugService
from .performance_monitor import GLMAgentPerformanceMonitor
from .smart_templates import get_all_templates, get_template_by_id, search_templates
from .structured_logger import get_logger, LogCategory, LogLevel
from .security_manager import GLMAgentSecurityManager

# Optional integrations
try:
    from .llm_integration import get_conversation_agent, async_get_api_response
    LLM_INTEGRATION_AVAILABLE = True
except ImportError:
    LLM_INTEGRATION_AVAILABLE = False

try:
    from .ai_task_pipeline import setup_ai_task_integration, create_ai_task_pipeline
    AI_TASK_PIPELINE_AVAILABLE = True
except ImportError:
    AI_TASK_PIPELINE_AVAILABLE = False

try:
    from .voice_pipeline import setup_voice_integration, create_voice_pipeline
    VOICE_PIPELINE_AVAILABLE = True
except ImportError:
    VOICE_PIPELINE_AVAILABLE = False

# Import config flow to ensure it's registered with Home Assistant
from . import config_flow  # noqa: F401

_LOGGER = logging.getLogger(__name__)

# Config schema - this integration only supports config entries
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


class HTTPRouteRegistry:
    """Registry for managing HTTP static routes to prevent duplicates."""

    def __init__(self):
        """Initialize the route registry."""
        self._registered_routes: Dict[str, SimpleNamespace] = {}
        self._static_paths: Set[str] = set()

    def is_route_registered(self, url_path: str) -> bool:
        """Check if a route is already registered."""
        return url_path in self._registered_routes

    def register_route(self, url_path: str, route_info: SimpleNamespace) -> bool:
        """Register a route if not already registered.

        Returns True if route was registered, False if it was already registered.
        """
        if self.is_route_registered(url_path):
            _LOGGER.warning("Route %s already registered, skipping registration", url_path)
            return False

        self._registered_routes[url_path] = route_info
        _LOGGER.debug("Registered HTTP route: %s", url_path)
        return True

    def unregister_route(self, url_path: str) -> bool:
        """Unregister a route.

        Returns True if route was unregistered, False if it wasn't found.
        """
        if url_path in self._registered_routes:
            del self._registered_routes[url_path]
            _LOGGER.debug("Unregistered HTTP route: %s", url_path)
            return True
        return False

    def is_static_path_registered(self, path: str) -> bool:
        """Check if a static path is already registered."""
        return path in self._static_paths

    def register_static_path(self, path: str) -> bool:
        """Register a static path if not already registered.

        Returns True if path was registered, False if it was already registered.
        """
        if self.is_static_path_registered(path):
            _LOGGER.warning("Static path %s already registered, skipping registration", path)
            return False

        self._static_paths.add(path)
        _LOGGER.debug("Registered static path: %s", path)
        return True

    def unregister_static_path(self, path: str) -> bool:
        """Unregister a static path.

        Returns True if path was unregistered, False if it wasn't found.
        """
        if path in self._static_paths:
            self._static_paths.remove(path)
            _LOGGER.debug("Unregistered static path: %s", path)
            return True
        return False

    def cleanup_all(self):
        """Clean up all registered routes and paths."""
        self._registered_routes.clear()
        self._static_paths.clear()
        _LOGGER.debug("Cleaned up all HTTP routes and static paths")

    def get_registered_routes(self) -> Dict[str, SimpleNamespace]:
        """Get all registered routes."""
        return dict(self._registered_routes)

    def get_registered_static_paths(self) -> Set[str]:
        """Get all registered static paths."""
        return set(self._static_paths)


# Global route registry instance
_ROUTE_REGISTRY: Optional[HTTPRouteRegistry] = None


def get_route_registry() -> HTTPRouteRegistry:
    """Get the global route registry instance."""
    global _ROUTE_REGISTRY
    if _ROUTE_REGISTRY is None:
        _ROUTE_REGISTRY = HTTPRouteRegistry()
    return _ROUTE_REGISTRY


async def async_register_static_route_with_validation(
    hass: HomeAssistant,
    url_path: str,
    file_path: str,
    cache_headers: bool = False
) -> bool:
    """Register a static route with validation and deduplication.

    Returns True if route was registered successfully, False otherwise.
    """
    try:
        # Validate HTTP component is ready
        if hass.http is None:
            _LOGGER.error("HTTP component not available for static route registration")
            return False

        if hass.http.app is None:
            _LOGGER.error("HTTP app not initialized for static route registration")
            return False

        if hass.http.app.router is None:
            _LOGGER.error("HTTP router not available for static route registration")
            return False

        # Validate file path exists
        import os
        if not os.path.exists(file_path):
            _LOGGER.error("Static file does not exist: %s", file_path)
            return False

        # Check if route already registered
        registry = get_route_registry()
        if registry.is_route_registered(url_path):
            _LOGGER.warning("Static route %s already registered, reusing existing route", url_path)
            return True

        # Create route configuration using StaticPathConfig for newer HA versions
        try:
            from homeassistant.components.http import StaticPathConfig
            route_config = StaticPathConfig(
                url_path=url_path,
                path=file_path,
                cache_headers=cache_headers
            )
            _LOGGER.debug("Using StaticPathConfig for HTTP route registration")
        except ImportError:
            # Fallback to SimpleNamespace for older HA versions
            route_config = SimpleNamespace(
                url_path=url_path,
                path=file_path,
                cache_headers=cache_headers,
                registered_at=time.time()
            )
            _LOGGER.debug("Using SimpleNamespace fallback for HTTP route registration")
        except Exception as e:
            _LOGGER.warning("Error creating StaticPathConfig, falling back to SimpleNamespace: %s", e)
            route_config = SimpleNamespace(
                url_path=url_path,
                path=file_path,
                cache_headers=cache_headers,
                registered_at=time.time()
            )

        # Register in our registry first
        if not registry.register_route(url_path, route_config):
            return False

        # Register with Home Assistant
        try:
            await hass.http.async_register_static_paths([route_config])
            _LOGGER.info("Successfully registered static route: %s -> %s", url_path, file_path)
            return True
        except Exception as e:
            # Rollback registration in our registry if HA registration failed
            registry.unregister_route(url_path)
            _LOGGER.error("Failed to register static route %s with Home Assistant: %s", url_path, e)
            return False

    except Exception as e:
        _LOGGER.error("Error registering static route %s: %s", url_path, e)
        return False


async def async_cleanup_registered_routes(hass: HomeAssistant):
    """Clean up all registered routes for this integration."""
    try:
        registry = get_route_registry()
        registered_routes = registry.get_registered_routes()

        # Note: Home Assistant doesn't provide a direct way to unregister static routes
        # but we clean up our registry to prevent accumulation
        registry.cleanup_all()

        _LOGGER.info("Cleaned up %d registered HTTP routes", len(registered_routes))

    except Exception as e:
        _LOGGER.error("Error cleaning up registered routes: %s", e)

# Define service schema to accept a custom prompt and optional attachment
SERVICE_SCHEMA = vol.Schema(
    {
        vol.Optional("prompt"): cv.string,
        vol.Optional("provider"): cv.string,
        vol.Optional("model"): cv.string,
        vol.Optional("structure"): dict,
        vol.Optional("attachment"): dict,
    }
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the GLM Coding Plan Agent HA component."""
    return True


async def _setup_pipeline_integrations(
    hass: HomeAssistant, config_data: Dict[str, Any], entry: ConfigEntry
) -> None:
    """Set up LLM and AI Task pipeline integrations."""

    # Set up AI Task pipeline integration
    if AI_TASK_PIPELINE_AVAILABLE:
        try:
            success = await setup_ai_task_integration(hass, config_data)
            if success:
                _LOGGER.info("AI Task pipeline integration setup completed")
            else:
                _LOGGER.warning("AI Task pipeline integration setup failed")
        except Exception as e:
            _LOGGER.error("Error setting up AI Task pipeline: %s", e)

    # Set up LLM integration (conversation agent)
    if LLM_INTEGRATION_AVAILABLE:
        try:
            # This will make GLM available in the Assist pipeline
            hass.data[DOMAIN]["conversation_agent"] = get_conversation_agent(
                hass, config_data, entry.entry_id
            )
            hass.data[DOMAIN]["llm_api_handler"] = async_get_api_response
            _LOGGER.info("LLM integration setup completed")
        except Exception as e:
            _LOGGER.error("Error setting up LLM integration: %s", e)

    # Set up voice integration
    if VOICE_PIPELINE_AVAILABLE:
        try:
            success = await setup_voice_integration(hass, config_data)
            if success:
                _LOGGER.info("Voice integration setup completed")
            else:
                _LOGGER.warning("Voice integration setup failed")
        except Exception as e:
            _LOGGER.error("Error setting up voice integration: %s", e)

    # Set up conversation platform for Assist (runtime check)
    try:
        # Import conversation module
        from homeassistant.components import conversation

        # Try to use the new ConversationEntity approach first
        try:
            from .conversation_entity import GLMAgentConversationEntity

            # Validate required parameters before creating entity
            if not all([hass, config_data, entry, entry.entry_id]):
                raise ValueError("Missing required parameters for ConversationEntity")

            conversation_entity = GLMAgentConversationEntity(hass, config_data, entry.entry_id)

            # Register the conversation entity with Home Assistant using the proper API
            from homeassistant.components import conversation
            conversation.async_set_agent(hass, entry, conversation_entity)
            _LOGGER.info("Conversation entity registered with Home Assistant using conversation.async_set_agent")

            # Store reference for cleanup
            hass.data[DOMAIN]["conversation_entity"] = conversation_entity

        except (ImportError, ValueError, TypeError, AttributeError) as e:
            _LOGGER.warning("Failed to set up conversation entity, falling back to agent approach: %s", e)
            # Clear any partially created entity reference
            if "conversation_entity" in hass.data[DOMAIN]:
                del hass.data[DOMAIN]["conversation_entity"]

            # Fallback to the original agent approach
            from .llm_integration import GLMConversationAgent
            agent = GLMConversationAgent(hass, config_data, entry.entry_id)

            # Register the conversation agent with Home Assistant using the proper API
            conversation.async_set_agent(hass, entry, agent)
            _LOGGER.info("Conversation agent registered with Home Assistant using conversation.async_set_agent")

            # Store reference for cleanup
            hass.data[DOMAIN]["conversation_agent"] = agent

    except ImportError:
        _LOGGER.debug("Conversation component not available in this HA version")
    except Exception as e:
        _LOGGER.error("Error setting up conversation platform: %s", e)

    # Set up AI Task platform (runtime check)
    try:
        # Check if AI task component is available
        try:
            from homeassistant.components import ai_task
            # If this import succeeds, AI task is available
            from .ai_task import async_setup_ai_task_entity
            ai_task_success = await async_setup_ai_task_entity(hass, config_data, entry)
            if ai_task_success:
                _LOGGER.info("AI Task platform setup completed")
                # Verify entity was created by checking hass.data
                if hasattr(hass, 'data') and 'entity_platform' in hass.data:
                    platform_data = hass.data.get('entity_platform', {})
                    ai_task_entities = platform_data.get('ai_task', {}).get('glm_agent_ha', [])
                    _LOGGER.info("AI Task entities created: %d", len(ai_task_entities))
            else:
                _LOGGER.debug("AI Task platform setup failed")
        except ImportError:
            _LOGGER.debug("AI Task platform not available in this HA version")
    except Exception as e:
        _LOGGER.error("Error setting up AI Task platform: %s", e)

    _LOGGER.info("All pipeline integrations setup completed")


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old config entries to new version."""
    _LOGGER.debug("Migrating config entry from version %s", entry.version)

    if entry.version == 1:
        # No migration needed for version 1
        return True

    # Future migrations would go here
    # if entry.version < 2:
    #     # Migrate from version 1 to 2
    #     new_data = dict(entry.data)
    #     # Add migration logic here
    #     hass.config_entries.async_update_entry(entry, data=new_data, version=2)

    _LOGGER.info("Migration to version %s successful", entry.version)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up GLM Coding Plan Agent HA from a config entry."""
    setup_start_time = time.time()
    try:
        # Handle version compatibility
        if not hasattr(entry, "version") or entry.version != 1:
            _LOGGER.warning(
                "Config entry has version %s, expected 1. Attempting compatibility mode.",
                getattr(entry, "version", "unknown"),
            )

        # Convert ConfigEntry to dict and ensure all required keys exist
        config_data = dict(entry.data)

        # Ensure backward compatibility - check for required keys
        if "ai_provider" not in config_data:
            _LOGGER.error(
                "Config entry missing required 'ai_provider' key. Entry data: %s",
                config_data,
            )
            raise ConfigEntryNotReady("Config entry missing required 'ai_provider' key")

        if DOMAIN not in hass.data:
            hass.data[DOMAIN] = {"agents": {}, "configs": {}, "debug_service": None, "performance_monitor": None, "structured_logger": None, "security_manager": None}

        # Initialize structured logger
        structured_logger = get_logger(hass, DOMAIN)
        hass.data[DOMAIN]["structured_logger"] = structured_logger
        structured_logger.info("GLM Agent HA integration setup started", LogCategory.SYSTEM,
                             version="1.11.1", config_entry_id=entry.entry_id, setup_start_time=setup_start_time)

        # Initialize debug service
        debug_service = GLMAgentDebugService(hass)
        hass.data[DOMAIN]["debug_service"] = debug_service
        structured_logger.debug("Debug service initialized", LogCategory.SYSTEM)

        # Initialize performance monitor
        performance_monitor = GLMAgentPerformanceMonitor(hass)
        hass.data[DOMAIN]["performance_monitor"] = performance_monitor
        structured_logger.debug("Performance monitor initialized", LogCategory.SYSTEM)

        # Initialize security manager
        security_manager = GLMAgentSecurityManager(hass)
        hass.data[DOMAIN]["security_manager"] = security_manager
        structured_logger.info("Security manager initialized", LogCategory.SECURITY,
                             rate_limiting=security_manager.enable_rate_limiting,
                             input_validation=security_manager.enable_input_validation,
                             threat_detection=security_manager.enable_threat_detection)

        provider = config_data["ai_provider"]

        # Validate provider
        if provider not in [
            "openai",
        ]:
            _LOGGER.error("Unknown AI provider: %s", provider)
            raise ConfigEntryNotReady(f"Unknown AI provider: {provider}")

        # Store config for this provider
        hass.data[DOMAIN]["configs"][provider] = config_data

        # Create agent for this provider
        _LOGGER.debug(
            "Creating AI agent for provider %s with config: %s",
            provider,
            {
                k: v
                for k, v in config_data.items()
                if k
                not in [
                    "openai_token",                            ]
            },
        )
        agent = AiAgentHaAgent(hass, config_data)
        hass.data[DOMAIN]["agents"][provider] = agent

        # Initialize MCP integration for Pro/Max plans (graceful fallback)
        if config_data.get("plan") in ["pro", "max"]:
            try:
                success = await agent.initialize_mcp_integration()
                if success:
                    _LOGGER.info("MCP integration initialized for plan: %s", config_data.get("plan"))
                else:
                    _LOGGER.warning("MCP integration not available - features will work without enhanced capabilities")
            except Exception as e:
                _LOGGER.warning("MCP integration failed - continuing without enhanced features: %s", e)

        # Set up conversation and AI task platforms
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

        # Log successful setup
        setup_duration_ms = (time.time() - setup_start_time) * 1000
        if structured_logger:
            structured_logger.info("GLM Agent HA integration setup completed successfully", LogCategory.SYSTEM,
                                 provider=provider, plan=config_data.get("plan"),
                                 duration_ms=setup_duration_ms, entry_id=entry.entry_id)
        _LOGGER.info("Successfully set up GLM Coding Plan Agent HA for provider: %s", provider)

    except KeyError as err:
        _LOGGER.error("Missing required configuration key: %s", err)
        raise ConfigEntryNotReady(f"Missing required configuration key: {err}")
    except Exception as err:
        _LOGGER.exception("Unexpected error setting up GLM Coding Plan Agent HA")
        raise ConfigEntryNotReady(f"Error setting up GLM Coding Plan Agent HA: {err}")

    # Modify the query service handler to use the correct provider
    async def async_handle_query(call):
        """Handle the query service call."""
        structured_logger = hass.data[DOMAIN].get("structured_logger")
        security_manager = hass.data[DOMAIN].get("security_manager")
        start_time = time.time()

        # Get client identifier for rate limiting
        client_id = call.context.user_id if call.context else "anonymous"
        if hasattr(call.context, 'connection') and call.context.connection:
            client_id = call.context.connection.client_ip or client_id

        # Security checks
        if security_manager:
            # Check rate limiting
            is_allowed, rate_info = security_manager.check_rate_limit(client_id)
            if not is_allowed:
                if structured_logger:
                    structured_logger.warning("Request rate limited", LogCategory.SECURITY,
                                              client_id=client_id, rate_info=rate_info)
                result = {"error": "Rate limit exceeded. Please try again later."}
                hass.bus.async_fire("glm_agent_ha_response", result)
                return

            # Validate input
            prompt = call.data.get("prompt", "")
            is_valid, error_msg = security_manager.validate_input(prompt, "prompt", 10000)
            if not is_valid:
                if structured_logger:
                    structured_logger.warning("Invalid input detected", LogCategory.SECURITY,
                                              client_id=client_id, error=error_msg)
                result = {"error": f"Invalid input: {error_msg}"}
                hass.bus.async_fire("glm_agent_ha_response", result)
                return

            # Detect anomalous activity
            is_anomalous, anomaly_reason = security_manager.detect_anomalous_activity(
                "api_call", client_id,
                {"prompt_length": len(prompt), "service": "query"}
            )
            if is_anomalous:
                if structured_logger:
                    structured_logger.warning("Anomalous activity detected", LogCategory.SECURITY,
                                              client_id=client_id, reason=anomaly_reason)
                # Continue but log the anomaly

        try:
            # Check if agents are available
            if DOMAIN not in hass.data or not hass.data[DOMAIN].get("agents"):
                if structured_logger:
                    structured_logger.error("No AI agents available", LogCategory.ERROR,
                                         user_id=call.context.user_id if call.context else None)
                result = {"error": "No AI agents configured"}
                hass.bus.async_fire("glm_agent_ha_response", result)
                return

            provider = call.data.get("provider")
            if provider not in hass.data[DOMAIN]["agents"]:
                # Get the first available provider
                available_providers = list(hass.data[DOMAIN]["agents"].keys())
                if not available_providers:
                    if structured_logger:
                        structured_logger.error("No AI agents available", LogCategory.ERROR,
                                             user_id=call.context.user_id if call.context else None)
                    result = {"error": "No AI agents configured"}
                    hass.bus.async_fire("glm_agent_ha_response", result)
                    return
                provider = available_providers[0]
                if structured_logger:
                    structured_logger.debug(f"Using fallback provider: {provider}", LogCategory.AI_AGENT)

            agent = hass.data[DOMAIN]["agents"][provider]

            # Log request start
            if structured_logger:
                structured_logger.info("Processing AI query request", LogCategory.AI_AGENT,
                                     provider=provider,
                                     model=call.data.get("model"),
                                     prompt_length=len(prompt),
                                     user_id=call.context.user_id if call.context else None,
                                     client_id=client_id)

            result = await agent.process_query(
                prompt,
                provider=provider,
                model=call.data.get("model"),
                structure=call.data.get("structure"),
                attachment=call.data.get("attachment"),
            )

            # Sanitize result for security
            if security_manager and isinstance(result, dict):
                result = security_manager.sanitize_data(result, "api_response")

            # Log request completion
            duration_ms = (time.time() - start_time) * 1000
            if structured_logger:
                structured_logger.info("AI query request completed", LogCategory.AI_AGENT,
                                     provider=provider,
                                     duration_ms=duration_ms,
                                     success=result.get("success", False),
                                     user_id=call.context.user_id if call.context else None,
                                     client_id=client_id)

            hass.bus.async_fire("glm_agent_ha_response", result)
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            if structured_logger:
                structured_logger.error("Error processing AI query request", LogCategory.ERROR,
                                     error_type=type(e).__name__,
                                     error_message=str(e),
                                     duration_ms=duration_ms,
                                     user_id=call.context.user_id if call.context else None,
                                     client_id=client_id,
                                     exc_info=True)
            result = {"error": str(e)}
            hass.bus.async_fire("glm_agent_ha_response", result)

    async def async_handle_create_automation(call):
        """Handle the create_automation service call."""
        try:
            # Check if agents are available
            if DOMAIN not in hass.data or not hass.data[DOMAIN].get("agents"):
                _LOGGER.error(
                    "No AI agents available. Please configure the integration first."
                )
                return {"error": "No AI agents configured"}

            provider = call.data.get("provider")
            if provider not in hass.data[DOMAIN]["agents"]:
                # Get the first available provider
                available_providers = list(hass.data[DOMAIN]["agents"].keys())
                if not available_providers:
                    _LOGGER.error("No AI agents available")
                    return {"error": "No AI agents configured"}
                provider = available_providers[0]
                _LOGGER.debug(f"Using fallback provider: {provider}")

            agent = hass.data[DOMAIN]["agents"][provider]
            result = await agent.create_automation(call.data.get("automation", {}))
            return result
        except Exception as e:
            _LOGGER.error(f"Error creating automation: {e}")
            return {"error": str(e)}

    async def async_handle_save_prompt_history(call):
        """Handle the save_prompt_history service call."""
        try:
            # Check if agents are available
            if DOMAIN not in hass.data or not hass.data[DOMAIN].get("agents"):
                _LOGGER.error(
                    "No AI agents available. Please configure the integration first."
                )
                return {"error": "No AI agents configured"}

            provider = call.data.get("provider")
            if provider not in hass.data[DOMAIN]["agents"]:
                # Get the first available provider
                available_providers = list(hass.data[DOMAIN]["agents"].keys())
                if not available_providers:
                    _LOGGER.error("No AI agents available")
                    return {"error": "No AI agents configured"}
                provider = available_providers[0]
                _LOGGER.debug(f"Using fallback provider: {provider}")

            agent = hass.data[DOMAIN]["agents"][provider]
            user_id = call.context.user_id if call.context.user_id else "default"
            result = await agent.save_user_prompt_history(
                user_id, call.data.get("history", [])
            )
            return result
        except Exception as e:
            _LOGGER.error(f"Error saving prompt history: {e}")
            return {"error": str(e)}

    async def async_handle_load_prompt_history(call):
        """Handle the load_prompt_history service call."""
        try:
            # Check if agents are available
            if DOMAIN not in hass.data or not hass.data[DOMAIN].get("agents"):
                _LOGGER.error(
                    "No AI agents available. Please configure the integration first."
                )
                return {"error": "No AI agents configured"}

            provider = call.data.get("provider")
            if provider not in hass.data[DOMAIN]["agents"]:
                # Get the first available provider
                available_providers = list(hass.data[DOMAIN]["agents"].keys())
                if not available_providers:
                    _LOGGER.error("No AI agents available")
                    return {"error": "No AI agents configured"}
                provider = available_providers[0]
                _LOGGER.debug(f"Using fallback provider: {provider}")

            agent = hass.data[DOMAIN]["agents"][provider]
            user_id = call.context.user_id if call.context.user_id else "default"
            result = await agent.load_user_prompt_history(user_id)
            _LOGGER.debug("Load prompt history result: %s", result)
            return result
        except Exception as e:
            _LOGGER.error(f"Error loading prompt history: {e}")
            return {"error": str(e)}

    async def async_handle_create_dashboard(call):
        """Handle the create_dashboard service call."""
        try:
            # Check if agents are available
            if DOMAIN not in hass.data or not hass.data[DOMAIN].get("agents"):
                _LOGGER.error(
                    "No AI agents available. Please configure the integration first."
                )
                return {"error": "No AI agents configured"}

            provider = call.data.get("provider")
            if provider not in hass.data[DOMAIN]["agents"]:
                # Get the first available provider
                available_providers = list(hass.data[DOMAIN]["agents"].keys())
                if not available_providers:
                    _LOGGER.error("No AI agents available")
                    return {"error": "No AI agents configured"}
                provider = available_providers[0]
                _LOGGER.debug(f"Using fallback provider: {provider}")

            agent = hass.data[DOMAIN]["agents"][provider]

            # Parse dashboard config if it's a string
            dashboard_config = call.data.get("dashboard_config", {})
            if isinstance(dashboard_config, str):
                try:
                    import json

                    dashboard_config = json.loads(dashboard_config)
                except json.JSONDecodeError as e:
                    _LOGGER.error(f"Invalid JSON in dashboard_config: {e}")
                    return {"error": f"Invalid JSON in dashboard_config: {e}"}

            result = await agent.create_dashboard(dashboard_config)
            return result
        except Exception as e:
            _LOGGER.error(f"Error creating dashboard: {e}")
            return {"error": str(e)}

    async def async_handle_update_dashboard(call):
        """Handle the update_dashboard service call."""
        try:
            # Check if agents are available
            if DOMAIN not in hass.data or not hass.data[DOMAIN].get("agents"):
                _LOGGER.error(
                    "No AI agents available. Please configure the integration first."
                )
                return {"error": "No AI agents configured"}

            provider = call.data.get("provider")
            if provider not in hass.data[DOMAIN]["agents"]:
                # Get the first available provider
                available_providers = list(hass.data[DOMAIN]["agents"].keys())
                if not available_providers:
                    _LOGGER.error("No AI agents available")
                    return {"error": "No AI agents configured"}
                provider = available_providers[0]
                _LOGGER.debug(f"Using fallback provider: {provider}")

            agent = hass.data[DOMAIN]["agents"][provider]

            # Parse dashboard config if it's a string
            dashboard_config = call.data.get("dashboard_config", {})
            if isinstance(dashboard_config, str):
                try:
                    import json

                    dashboard_config = json.loads(dashboard_config)
                except json.JSONDecodeError as e:
                    _LOGGER.error(f"Invalid JSON in dashboard_config: {e}")
                    return {"error": f"Invalid JSON in dashboard_config: {e}"}

            dashboard_url = call.data.get("dashboard_url", "")
            if not dashboard_url:
                return {"error": "Dashboard URL is required"}

            result = await agent.update_dashboard(dashboard_url, dashboard_config)
            return result
        except Exception as e:
            _LOGGER.error(f"Error updating dashboard: {e}")
            return {"error": str(e)}

    # Debug service handlers
    async def async_handle_debug_info(call):
        """Handle the debug_info service call."""
        try:
            if DOMAIN not in hass.data or not hass.data[DOMAIN].get("debug_service"):
                return {"error": "Debug service not available"}

            debug_service = hass.data[DOMAIN]["debug_service"]
            entry_id = call.data.get("entry_id")

            result = await debug_service.get_integration_status(entry_id)
            _LOGGER.debug("Debug info requested: %s", result.get("integration_status", "unknown"))
            return result
        except Exception as e:
            _LOGGER.error(f"Error getting debug info: {e}")
            return {"error": str(e)}

    async def async_handle_debug_system(call):
        """Handle the debug_system service call."""
        try:
            if DOMAIN not in hass.data or not hass.data[DOMAIN].get("debug_service"):
                return {"error": "Debug service not available"}

            debug_service = hass.data[DOMAIN]["debug_service"]
            result = await debug_service.get_system_info()
            _LOGGER.debug("System debug info requested")
            return result
        except Exception as e:
            _LOGGER.error(f"Error getting system debug info: {e}")
            return {"error": str(e)}

    async def async_handle_debug_api(call):
        """Handle the debug_api service call."""
        try:
            if DOMAIN not in hass.data or not hass.data[DOMAIN].get("debug_service"):
                return {"error": "Debug service not available"}

            debug_service = hass.data[DOMAIN]["debug_service"]
            entry_id = call.data.get("entry_id")

            result = await debug_service.test_api_connections(entry_id)
            _LOGGER.debug("API connection test requested")
            return result
        except Exception as e:
            _LOGGER.error(f"Error testing API connections: {e}")
            return {"error": str(e)}

    async def async_handle_debug_logs(call):
        """Handle the debug_logs service call."""
        try:
            if DOMAIN not in hass.data or not hass.data[DOMAIN].get("debug_service"):
                return {"error": "Debug service not available"}

            debug_service = hass.data[DOMAIN]["debug_service"]
            entry_id = call.data.get("entry_id")
            lines = call.data.get("lines", 100)

            result = await debug_service.get_service_logs(entry_id, lines)
            _LOGGER.debug("Service logs requested")
            return result
        except Exception as e:
            _LOGGER.error(f"Error getting service logs: {e}")
            return {"error": str(e)}

    async def async_handle_debug_report(call):
        """Handle the debug_report service call."""
        try:
            if DOMAIN not in hass.data or not hass.data[DOMAIN].get("debug_service"):
                return {"error": "Debug service not available"}

            debug_service = hass.data[DOMAIN]["debug_service"]
            entry_id = call.data.get("entry_id")

            result = await debug_service.generate_debug_report(entry_id)
            _LOGGER.info("Comprehensive debug report generated")
            return result
        except Exception as e:
            _LOGGER.error(f"Error generating debug report: {e}")
            return {"error": str(e)}

    # Performance monitoring service handlers
    async def async_handle_performance_current(call):
        """Handle the performance_current service call."""
        try:
            if DOMAIN not in hass.data or not hass.data[DOMAIN].get("performance_monitor"):
                return {"error": "Performance monitor not available"}

            monitor = hass.data[DOMAIN]["performance_monitor"]
            result = monitor.get_current_metrics()
            _LOGGER.debug("Current performance metrics requested")
            return result
        except Exception as e:
            _LOGGER.error(f"Error getting current performance metrics: {e}")
            return {"error": str(e)}

    async def async_handle_performance_aggregated(call):
        """Handle the performance_aggregated service call."""
        try:
            if DOMAIN not in hass.data or not hass.data[DOMAIN].get("performance_monitor"):
                return {"error": "Performance monitor not available"}

            monitor = hass.data[DOMAIN]["performance_monitor"]
            period_hours = call.data.get("period_hours", 24)

            result = monitor.get_aggregated_metrics(period_hours)
            _LOGGER.debug("Aggregated performance metrics requested for %d hours", period_hours)
            return result
        except Exception as e:
            _LOGGER.error(f"Error getting aggregated performance metrics: {e}")
            return {"error": str(e)}

    async def async_handle_performance_trends(call):
        """Handle the performance_trends service call."""
        try:
            if DOMAIN not in hass.data or not hass.data[DOMAIN].get("performance_monitor"):
                return {"error": "Performance monitor not available"}

            monitor = hass.data[DOMAIN]["performance_monitor"]
            days = call.data.get("days", 7)

            result = monitor.get_performance_trends(days)
            _LOGGER.debug("Performance trends requested for %d days", days)
            return result
        except Exception as e:
            _LOGGER.error(f"Error getting performance trends: {e}")
            return {"error": str(e)}

    async def async_handle_performance_slow_requests(call):
        """Handle the performance_slow_requests service call."""
        try:
            if DOMAIN not in hass.data or not hass.data[DOMAIN].get("performance_monitor"):
                return {"error": "Performance monitor not available"}

            monitor = hass.data[DOMAIN]["performance_monitor"]
            limit = call.data.get("limit", 10)

            result = monitor.get_top_slow_requests(limit)
            _LOGGER.debug("Slow requests requested with limit %d", limit)
            return result
        except Exception as e:
            _LOGGER.error(f"Error getting slow requests: {e}")
            return {"error": str(e)}

    async def async_handle_performance_export(call):
        """Handle the performance_export service call."""
        try:
            if DOMAIN not in hass.data or not hass.data[DOMAIN].get("performance_monitor"):
                return {"error": "Performance monitor not available"}

            monitor = hass.data[DOMAIN]["performance_monitor"]
            format_type = call.data.get("format", "json")

            result = monitor.export_metrics(format_type)
            _LOGGER.info("Performance metrics exported in %s format", format_type)
            return {"export_data": result, "format": format_type, "timestamp": datetime.now().isoformat()}
        except Exception as e:
            _LOGGER.error(f"Error exporting performance metrics: {e}")
            return {"error": str(e)}

    async def async_handle_performance_reset(call):
        """Handle the performance_reset service call."""
        try:
            if DOMAIN not in hass.data or not hass.data[DOMAIN].get("performance_monitor"):
                return {"error": "Performance monitor not available"}

            monitor = hass.data[DOMAIN]["performance_monitor"]
            monitor.reset_metrics()

            structured_logger = hass.data[DOMAIN].get("structured_logger")
            if structured_logger:
                structured_logger.info("Performance metrics reset by user request", LogCategory.SYSTEM)

            return {"message": "Performance metrics reset successfully"}
        except Exception as e:
            _LOGGER.error(f"Error resetting performance metrics: {e}")
            return {"error": str(e)}

    # Structured logging service handlers
    async def async_handle_logging_stats(call):
        """Handle the logging_stats service call."""
        try:
            if DOMAIN not in hass.data or not hass.data[DOMAIN].get("structured_logger"):
                return {"error": "Structured logger not available"}

            structured_logger = hass.data[DOMAIN]["structured_logger"]
            stats = structured_logger.get_statistics()

            structured_logger.debug("Logging statistics requested", LogCategory.SYSTEM)
            return stats
        except Exception as e:
            _LOGGER.error(f"Error getting logging statistics: {e}")
            return {"error": str(e)}

    async def async_handle_logging_search(call):
        """Handle the logging_search service call."""
        try:
            if DOMAIN not in hass.data or not hass.data[DOMAIN].get("structured_logger"):
                return {"error": "Structured logger not available"}

            structured_logger = hass.data[DOMAIN]["structured_logger"]
            query = call.data.get("query", "")
            category = call.data.get("category")
            level = call.data.get("level")
            limit = call.data.get("limit", 100)

            # Convert string category/level to enums if provided
            category_enum = None
            if category:
                try:
                    category_enum = LogCategory(category.lower())
                except ValueError:
                    pass

            level_enum = None
            if level:
                try:
                    level_enum = LogLevel(level.upper())
                except ValueError:
                    pass

            results = structured_logger.search_logs(query, category_enum, level_enum, limit)

            structured_logger.info("Log search performed", LogCategory.SYSTEM,
                                 query=query, category=category, level=level, results_count=len(results))

            return {
                "query": query,
                "category": category,
                "level": level,
                "limit": limit,
                "results_count": len(results),
                "results": results
            }
        except Exception as e:
            _LOGGER.error(f"Error searching logs: {e}")
            return {"error": str(e)}

    # Security service handlers
    async def async_handle_security_report(call):
        """Handle the security_report service call."""
        try:
            if DOMAIN not in hass.data or not hass.data[DOMAIN].get("security_manager"):
                return {"error": "Security manager not available"}

            security_manager = hass.data[DOMAIN]["security_manager"]
            hours = call.data.get("hours", 24)

            report = security_manager.get_security_report(hours)

            if structured_logger:
                structured_logger.info("Security report generated", LogCategory.SECURITY,
                                     hours=hours, total_events=report["total_events"])

            return report
        except Exception as e:
            _LOGGER.error(f"Error generating security report: {e}")
            return {"error": str(e)}

    async def async_handle_security_validate(call):
        """Handle the security_validate service call."""
        try:
            if DOMAIN not in hass.data or not hass.data[DOMAIN].get("security_manager"):
                return {"error": "Security manager not available"}

            security_manager = hass.data[DOMAIN]["security_manager"]
            input_data = call.data.get("input", "")
            input_type = call.data.get("type", "general")

            is_valid, error_msg = security_manager.validate_input(input_data, input_type)

            if structured_logger:
                level = LogCategory.SECURITY if is_valid else LogCategory.ERROR
                action = "validation_passed" if is_valid else "validation_failed"
                structured_logger.info(f"Input {action}", level,
                                     input_type=input_type, length=len(input_data),
                                     error=error_msg if not is_valid else None)

            return {
                "input_type": input_type,
                "input_length": len(input_data),
                "is_valid": is_valid,
                "error_message": error_msg
            }
        except Exception as e:
            _LOGGER.error(f"Error validating input: {e}")
            return {"error": str(e)}

    async def async_handle_security_block(call):
        """Handle the security_block service call."""
        try:
            if DOMAIN not in hass.data or not hass.data[DOMAIN].get("security_manager"):
                return {"error": "Security manager not available"}

            security_manager = hass.data[DOMAIN]["security_manager"]
            identifier = call.data.get("identifier", "")
            reason = call.data.get("reason", "Manual block")
            duration_hours = call.data.get("duration", 24)

            if not identifier:
                return {"error": "Identifier is required"}

            security_manager.block_identifier(identifier, reason, duration_hours)

            if structured_logger:
                structured_logger.warning("Identifier blocked", LogCategory.SECURITY,
                                             identifier=identifier, reason=reason,
                                             duration_hours=duration_hours)

            return {
                "identifier": identifier,
                "reason": reason,
                "duration_hours": duration_hours,
                "blocked_at": datetime.now().isoformat()
            }
        except Exception as e:
            _LOGGER.error(f"Error blocking identifier: {e}")
            return {"error": str(e)}

    async def async_handle_security_domains(call):
        """Handle the security_domains service call."""
        try:
            if DOMAIN not in hass.data or not hass.data[DOMAIN].get("security_manager"):
                return {"error": "Security manager not available"}

            security_manager = hass.data[DOMAIN]["security_manager"]
            action = call.data.get("action", "list")  # list, add, remove
            domain = call.data.get("domain", "")

            if action == "list":
                return {
                    "allowed_domains": list(security_manager.get_allowed_domains()),
                    "total_count": len(security_manager.get_allowed_domains())
                }
            elif action == "add":
                if not domain:
                    return {"error": "Domain is required for add action"}
                security_manager.add_allowed_domain(domain)
                return {
                    "action": "added",
                    "domain": domain,
                    "allowed_domains": list(security_manager.get_allowed_domains())
                }
            elif action == "remove":
                if not domain:
                    return {"error": "Domain is required for remove action"}
                security_manager.remove_allowed_domain(domain)
                return {
                    "action": "removed",
                    "domain": domain,
                    "allowed_domains": list(security_manager.get_allowed_domains())
                }
            else:
                return {"error": f"Invalid action: {action}"}

        except Exception as e:
            _LOGGER.error(f"Error managing domains: {e}")
            return {"error": str(e)}

    # Smart template service handlers
    async def async_handle_get_templates(call):
        """Handle the get_templates service call."""
        try:
            template_category = call.data.get("category")
            template_id = call.data.get("template_id")
            search_query = call.data.get("search")

            if template_id:
                # Get specific template
                template = get_template_by_id(template_id)
                result = {"template": template}
            elif template_category:
                # Get templates by category
                from .smart_templates import get_templates_by_category
                templates = get_templates_by_category(template_category)
                result = {"category": template_category, "templates": templates}
            elif search_query:
                # Search templates
                templates = search_templates(search_query)
                result = {"query": search_query, "templates": templates}
            else:
                # Get all templates
                result = get_all_templates()

            if structured_logger:
                structured_logger.info("Templates retrieved", LogCategory.SYSTEM,
                                     category=template_category, template_id=template_id,
                                     search_query=search_query)

            return result
        except Exception as e:
            _LOGGER.error(f"Error getting templates: %s", e)
            return {"error": str(e)}

    async def async_handle_apply_template(call):
        """Handle the apply_template service call."""
        try:
            # Check if agents are available
            if DOMAIN not in hass.data or not hass.data[DOMAIN].get("agents"):
                _LOGGER.error("No AI agents available for template application")
                return {"error": "No AI agents configured"}

            template_id = call.data.get("template_id")
            if not template_id:
                return {"error": "Template ID is required"}

            # Get template details
            template = get_template_by_id(template_id)
            if not template:
                return {"error": f"Template not found: {template_id}"}

            # Get available provider
            available_providers = list(hass.data[DOMAIN]["agents"].keys())
            if not available_providers:
                return {"error": "No AI agents available"}

            provider = available_providers[0]
            agent = hass.data[DOMAIN]["agents"][provider]

            # Process the template with AI
            result = await agent.process_query(
                prompt=template.get("prompt", ""),
                context={
                    "template_name": template.get("name"),
                    "template_category": template.get("category"),
                    "template_complexity": template.get("complexity"),
                    "requested_by": "template_service"
                }
            )

            if structured_logger:
                structured_logger.info("Template applied", LogCategory.AI_AGENT,
                                     template_id=template_id, template_name=template.get("name"),
                                     provider=provider, success=result.get("success", False))

            return {
                "template_id": template_id,
                "template_name": template.get("name"),
                "result": result,
                "estimated_time": template.get("estimated_time"),
                "complexity": template.get("complexity")
            }

        except Exception as e:
            _LOGGER.error(f"Error applying template: %s", e)
            return {"error": str(e)}

    # Register services
    hass.services.async_register(DOMAIN, "query", async_handle_query)
    hass.services.async_register(
        DOMAIN, "create_automation", async_handle_create_automation
    )
    hass.services.async_register(
        DOMAIN, "save_prompt_history", async_handle_save_prompt_history
    )
    hass.services.async_register(
        DOMAIN, "load_prompt_history", async_handle_load_prompt_history
    )
    hass.services.async_register(
        DOMAIN, "create_dashboard", async_handle_create_dashboard
    )
    hass.services.async_register(
        DOMAIN, "update_dashboard", async_handle_update_dashboard
    )

    # Register debug services
    hass.services.async_register(DOMAIN, "debug_info", async_handle_debug_info)
    hass.services.async_register(DOMAIN, "debug_system", async_handle_debug_system)
    hass.services.async_register(DOMAIN, "debug_api", async_handle_debug_api)
    hass.services.async_register(DOMAIN, "debug_logs", async_handle_debug_logs)
    hass.services.async_register(DOMAIN, "debug_report", async_handle_debug_report)

    # Register performance monitoring services
    hass.services.async_register(DOMAIN, "performance_current", async_handle_performance_current)
    hass.services.async_register(DOMAIN, "performance_aggregated", async_handle_performance_aggregated)
    hass.services.async_register(DOMAIN, "performance_trends", async_handle_performance_trends)
    hass.services.async_register(DOMAIN, "performance_slow_requests", async_handle_performance_slow_requests)
    hass.services.async_register(DOMAIN, "performance_export", async_handle_performance_export)
    hass.services.async_register(DOMAIN, "performance_reset", async_handle_performance_reset)

    # Register structured logging services
    hass.services.async_register(DOMAIN, "logging_stats", async_handle_logging_stats)
    hass.services.async_register(DOMAIN, "logging_search", async_handle_logging_search)

    # Register security services
    hass.services.async_register(DOMAIN, "security_report", async_handle_security_report)
    hass.services.async_register(DOMAIN, "security_validate", async_handle_security_validate)
    hass.services.async_register(DOMAIN, "security_block", async_handle_security_block)
    hass.services.async_register(DOMAIN, "security_domains", async_handle_security_domains)

    # Register smart template services
    hass.services.async_register(DOMAIN, "get_templates", async_handle_get_templates)
    hass.services.async_register(DOMAIN, "apply_template", async_handle_apply_template)

    # Log successful service registration
    structured_logger = hass.data[DOMAIN].get("structured_logger")
    if structured_logger:
        structured_logger.info("All GLM Agent HA services registered successfully", LogCategory.SYSTEM,
                             debug_services=5, performance_services=6, logging_services=2, security_services=4, template_services=2)

    _LOGGER.debug("Debug, performance, logging, and security services registered successfully")

    # Register static path for frontend with improved error handling and HTTP component validation
    static_route_success = False
    max_retries = 5
    retry_delay = 2  # seconds

    for attempt in range(max_retries):
        try:
            # Validate HTTP component is ready before attempting registration
            if not hasattr(hass, 'http') or hass.http is None:
                _LOGGER.warning("HTTP component not available on attempt %d, retrying...", attempt + 1)
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 1.5, 10)  # Cap at 10 seconds
                continue

            if not hasattr(hass.http, 'app') or hass.http.app is None:
                _LOGGER.warning("HTTP app not initialized on attempt %d, retrying...", attempt + 1)
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 1.5, 10)
                continue

            if not hasattr(hass.http.app, 'router') or hass.http.app.router is None:
                _LOGGER.warning("HTTP router not available on attempt %d, retrying...", attempt + 1)
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 1.5, 10)
                continue

            # Attempt registration with validated HTTP component
            static_route_success = await async_register_static_route_with_validation(
                hass,
                "/frontend/glm_agent_ha/glm_agent_ha-panel.js",
                hass.config.path("custom_components/glm_agent_ha/frontend/glm_agent_ha-panel.js"),
                cache_headers=False,
            )

            if static_route_success:
                _LOGGER.info("Successfully registered static route for GLM Agent HA panel")
                break

        except Exception as e:
            _LOGGER.error("HTTP registration attempt %d failed with error: %s", attempt + 1, e)
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 15)  # Exponential backoff, cap at 15 seconds

    if not static_route_success:
        _LOGGER.error("Failed to register static route for frontend panel after %d attempts - dashboard features will be unavailable", max_retries)
        # Continue with setup but log the failure prominently

    # Panel registration with proper error handling
    panel_name = "glm_agent_ha"
    try:
        if await _panel_exists(hass, panel_name):
            _LOGGER.debug("GLM Coding Plan Agent HA panel already exists, skipping registration")

        _LOGGER.debug("Registering GLM Coding Plan Agent HA panel")
        async_register_built_in_panel(
            hass,
            component_name="custom",
            sidebar_title="GLM Coding Plan Agent HA",
            sidebar_icon="mdi:robot",
            frontend_url_path=panel_name,
            require_admin=False,
            config={
                "_panel_custom": {
                    "name": "glm_agent_ha-panel",
                    "module_url": "/frontend/glm_agent_ha/glm_agent_ha-panel.js",
                    "embed_iframe": False,
                }
            },
        )
        _LOGGER.debug("GLM Coding Plan Agent HA panel registered successfully")
    except Exception as e:
        _LOGGER.warning("Panel registration error: %s", str(e))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    # Unload platforms first
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Unregister conversation agent using the proper API
        try:
            from homeassistant.components import conversation

            # Try to unregister the conversation agent
            conversation.async_unset_agent(hass, entry)
            _LOGGER.info("Conversation agent unregistered from Home Assistant")

        except ImportError:
            _LOGGER.debug("Conversation component not available for unregistration")
        except Exception as e:
            _LOGGER.warning("Failed to unregister conversation agent: %s", e)

    if await _panel_exists(hass, "glm_agent_ha"):
        try:
            from homeassistant.components.frontend import async_remove_panel

            async_remove_panel(hass, "glm_agent_ha")
            _LOGGER.debug("GLM Coding Plan Agent HA panel removed successfully")
        except Exception as e:
            _LOGGER.debug("Error removing panel: %s", str(e))

    # Clean up registered HTTP routes
    await async_cleanup_registered_routes(hass)

    # Remove services
    hass.services.async_remove(DOMAIN, "query")
    hass.services.async_remove(DOMAIN, "create_automation")
    hass.services.async_remove(DOMAIN, "save_prompt_history")
    hass.services.async_remove(DOMAIN, "load_prompt_history")
    hass.services.async_remove(DOMAIN, "create_dashboard")
    hass.services.async_remove(DOMAIN, "update_dashboard")

    # Remove debug services
    hass.services.async_remove(DOMAIN, "debug_info")
    hass.services.async_remove(DOMAIN, "debug_system")
    hass.services.async_remove(DOMAIN, "debug_api")
    hass.services.async_remove(DOMAIN, "debug_logs")
    hass.services.async_remove(DOMAIN, "debug_report")

    # Remove performance monitoring services
    hass.services.async_remove(DOMAIN, "performance_current")
    hass.services.async_remove(DOMAIN, "performance_aggregated")
    hass.services.async_remove(DOMAIN, "performance_trends")
    hass.services.async_remove(DOMAIN, "performance_slow_requests")
    hass.services.async_remove(DOMAIN, "performance_export")
    hass.services.async_remove(DOMAIN, "performance_reset")

    # Remove structured logging services
    hass.services.async_remove(DOMAIN, "logging_stats")
    hass.services.async_remove(DOMAIN, "logging_search")

    # Remove security services
    hass.services.async_remove(DOMAIN, "security_report")
    hass.services.async_remove(DOMAIN, "security_validate")
    hass.services.async_remove(DOMAIN, "security_block")
    hass.services.async_remove(DOMAIN, "security_domains")

    # Remove template services
    hass.services.async_remove(DOMAIN, "get_templates")
    hass.services.async_remove(DOMAIN, "apply_template")

    # Remove data only if platforms unloaded successfully
    if unload_ok and DOMAIN in hass.data:
        # Only remove the data for this entry, keep others
        if entry.entry_id in hass.data[DOMAIN].get("configs", {}):
            del hass.data[DOMAIN]["configs"][entry.entry_id]
        if entry.entry_id in hass.data[DOMAIN].get("agents", {}):
            del hass.data[DOMAIN]["agents"][entry.entry_id]

    return unload_ok


async def _panel_exists(hass: HomeAssistant, panel_name: str) -> bool:
    """Check if a panel already exists."""
    try:
        return panel_name in hass.data.get("frontend_panels", {})
    except Exception as e:
        _LOGGER.debug("Error checking panel existence: %s", str(e))
        return False
