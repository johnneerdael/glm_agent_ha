"""GLM Agent HA conversation platform.

This module provides the platform setup for GLM Agent HA conversation entities,
following the proper Home Assistant platform registration pattern.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .conversation_entity import GLMAgentConversationEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up GLM Agent HA conversation entities.

    This function is called by Home Assistant when setting up the conversation
    platform for this integration. It creates the conversation entity and
    registers it with Home Assistant's conversation system.

    Args:
        hass: The Home Assistant instance.
        config_entry: The config entry for this integration.
        async_add_entities: Callback to add entities to Home Assistant.

    Raises:
        ValueError: If required configuration parameters are missing.
        TypeError: If configuration parameters have invalid types.
    """
    _LOGGER.debug("Setting up GLM Agent HA conversation platform for entry: %s", config_entry.entry_id)

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

        # Create the conversation entity - fix constructor parameters to match entity expectations
        conversation_entity = GLMAgentConversationEntity(
            hass=hass,
            entry=config_entry,
            client=None  # The entity handles AI processing internally
        )

        _LOGGER.info("Created GLM Agent conversation entity: %s", conversation_entity.entity_id)

        # Add the entity to Home Assistant
        async_add_entities([conversation_entity], True)

        _LOGGER.info("Successfully set up GLM Agent HA conversation platform")

    except (ValueError, TypeError) as e:
        _LOGGER.error("Configuration validation failed for conversation platform: %s", e)
        raise
    except Exception as e:
        _LOGGER.error("Failed to set up GLM Agent HA conversation platform: %s", e)
        raise