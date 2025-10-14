"""The GLM Coding Plan Agent HA integration."""

from __future__ import annotations

import logging
import time
from datetime import datetime
from types import SimpleNamespace

import voluptuous as vol
from homeassistant.components.ai_task import async_setup_ai_task
from homeassistant.components.frontend import async_register_built_in_panel
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .agent import AiAgentHaAgent
from .const import (
    CONF_ENABLE_AI_TASK,
    DOMAIN,
)
from .debug_service import GLMAgentDebugService
from .performance_monitor import GLMAgentPerformanceMonitor
from .structured_logger import get_logger, LogCategory, LogLevel
from .security_manager import GLMAgentSecurityManager

# Import config flow to ensure it's registered with Home Assistant
from . import config_flow  # noqa: F401

_LOGGER = logging.getLogger(__name__)

# Config schema - this integration only supports config entries
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

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
                             version="1.06.0", config_entry_id=entry.entry_id, setup_start_time=setup_start_time)

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

        # Initialize MCP integration for Pro/Max plans
        if config_data.get("plan") in ["pro", "max"]:
            try:
                await agent.initialize_mcp_integration()
                _LOGGER.info("MCP integration initialized for plan: %s", config_data.get("plan"))
            except Exception as e:
                _LOGGER.error("Failed to initialize MCP integration: %s", e)

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

    # Log successful service registration
    structured_logger = hass.data[DOMAIN].get("structured_logger")
    if structured_logger:
        structured_logger.info("All GLM Agent HA services registered successfully", LogCategory.SYSTEM,
                             debug_services=5, performance_services=6, logging_services=2, security_services=4)

    _LOGGER.debug("Debug, performance, logging, and security services registered successfully")

    # Register static path for frontend
    await hass.http.async_register_static_paths([
        SimpleNamespace(
            url_path="/frontend/glm_agent_ha/glm_agent_ha-panel.js",
            path=hass.config.path("custom_components/glm_agent_ha/frontend/glm_agent_ha-panel.js"),
            cache_headers=False,
        )
    ])

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

    # Set up AI Task entity if enabled
    if entry.options.get(CONF_ENABLE_AI_TASK, True):
        try:
            await hass.config_entries.async_forward_entry_setup(entry, "ai_task")
            _LOGGER.info("AI Task entity platform setup completed")
        except Exception as e:
            _LOGGER.error("Failed to set up AI Task entity platform: %s", e)
            # Don't fail the entire setup for AI Task platform issues

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload AI Task entity platform if it was set up
    if entry.options.get(CONF_ENABLE_AI_TASK, True):
        try:
            await hass.config_entries.async_forward_entry_unload(entry, "ai_task")
            _LOGGER.debug("AI Task entity platform unloaded")
        except Exception as e:
            _LOGGER.debug("Error unloading AI Task entity platform: %s", str(e))

    if await _panel_exists(hass, "glm_agent_ha"):
        try:
            from homeassistant.components.frontend import async_remove_panel

            async_remove_panel(hass, "glm_agent_ha")
            _LOGGER.debug("GLM Coding Plan Agent HA panel removed successfully")
        except Exception as e:
            _LOGGER.debug("Error removing panel: %s", str(e))

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
    # Remove data
    if DOMAIN in hass.data:
        hass.data.pop(DOMAIN)

    return True


async def _panel_exists(hass: HomeAssistant, panel_name: str) -> bool:
    """Check if a panel already exists."""
    try:
        return panel_name in hass.data.get("frontend_panels", {})
    except Exception as e:
        _LOGGER.debug("Error checking panel existence: %s", str(e))
        return False
