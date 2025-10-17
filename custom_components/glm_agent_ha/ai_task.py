"""GLM Agent HA AI Task platform.

This module provides the platform setup for GLM Agent HA AI Task entities,
following the proper Home Assistant platform registration pattern.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .ai_task_entity import GLMAgentAITaskEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up GLM Agent HA AI Task entities.

    This function is called by Home Assistant when setting up the AI Task
    platform for this integration. It creates the AI Task entity and
    registers it with Home Assistant's AI Task system.

    Args:
        hass: The Home Assistant instance.
        config_entry: The config entry for this integration.
        async_add_entities: Callback to add entities to Home Assistant.

    Raises:
        ValueError: If required configuration parameters are missing.
        TypeError: If configuration parameters have invalid types.
    """
    _LOGGER.debug("Setting up GLM Agent HA AI Task platform for entry: %s", config_entry.entry_id)

    try:
        # Validate required parameters
        if not hass:
            raise ValueError("Home Assistant instance is required")
        if not config_entry:
            raise ValueError("Config entry is required")
        if not config_entry.entry_id:
            raise ValueError("Config entry ID is required")
        if not config_entry.data:
            raise ValueError("Config entry data is required")

        # Create the AI Task entity
        ai_task_entity = GLMAgentAITaskEntity(hass, config_entry)

        _LOGGER.info("Created GLM Agent AI Task entity: %s", ai_task_entity.entity_id)

        # Add the entity to Home Assistant
        async_add_entities([ai_task_entity], True)

        _LOGGER.info("Successfully set up GLM Agent HA AI Task platform")

    except (ValueError, TypeError) as e:
        _LOGGER.error("Configuration validation failed for AI Task platform: %s", e)
        raise
    except Exception as e:
        _LOGGER.error("Failed to set up GLM Agent HA AI Task platform: %s", e)
        raise