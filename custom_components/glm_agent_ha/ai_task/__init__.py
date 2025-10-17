"""AI Task platform for GLM Agent HA integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.ai_task import AITaskEntityDescription, AITaskEntityFeature, async_setup_ai_task_platform
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from ..const import (
    CONF_AI_PROVIDER,
    CONF_ENABLE_AI_TASK,
    DOMAIN,
)
from ..ai_task_entity import GLMAgentAITaskEntity

_LOGGER = logging.getLogger(__name__)

# AI Task entity description
AI_TASK_ENTITY_DESCRIPTION = AITaskEntityDescription(
    key="glm_agent_ai_task",
    name="GLM Agent AI Task",
    supported_features=AITaskEntityFeature.GENERATE_DATA,
    has_entity_name=True,
)


async def async_setup_ai_task_entity(
    hass: HomeAssistant,
    config: ConfigType,
    entry: ConfigEntry,
) -> bool:
    """Set up the AI Task platform."""
    _LOGGER.debug("Setting up AI Task platform for GLM Agent HA")

    try:
        # Check if AI Task is enabled
        if not entry.options.get(CONF_ENABLE_AI_TASK, True):
            _LOGGER.debug("AI Task entity disabled in options")
            return False

        # Check if AI provider is configured
        if CONF_AI_PROVIDER not in entry.data:
            _LOGGER.error("No AI provider configured for AI Task entity")
            return False

        # Create AI Task entity description
        ai_task_entity_description = AITaskEntityDescription(
            key="glm_agent_ai_task",
            name="GLM Agent AI Task",
            supported_features=AITaskEntityFeature.GENERATE_DATA,
            has_entity_name=True,
        )

        # Register AI Task platform
        await async_setup_ai_task_platform(
            hass,
            DOMAIN,
            ai_task_entity_description,
            lambda hass, config, async_add_entities, discovery_info=None:
                _setup_ai_task_entities(hass, config, async_add_entities, entry)
        )

        _LOGGER.info("AI Task platform setup completed for GLM Agent HA")
        return True

    except Exception as e:
        _LOGGER.error("Error setting up AI Task platform: %s", e)
        return False

async def _setup_ai_task_entities(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    entry: ConfigEntry,
) -> None:
    """Set up AI Task entities."""
    try:
        # Create and add the AI Task entity
        entity = GLMAgentAITaskEntity(hass, entry)
        async_add_entities([entity], True)

        _LOGGER.info("AI Task entity added for GLM Agent HA: %s", entity.entity_id)
    except Exception as e:
        _LOGGER.error("Error setting up AI Task entity: %s", e)