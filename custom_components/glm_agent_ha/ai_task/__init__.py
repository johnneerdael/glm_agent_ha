"""AI Task platform for GLM Agent HA integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.ai_task import AITaskEntityDescription, AITaskEntityFeature, async_setup_ai_task_platform
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


async def async_setup_ai_task(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the AI Task platform."""
    _LOGGER.debug("Setting up AI Task platform for GLM Agent HA")
    
    # Get config entry from discovery info
    if discovery_info is None:
        _LOGGER.error("No discovery info for AI Task platform setup")
        return
    
    entry_id = discovery_info.get("entry_id")
    if entry_id is None:
        _LOGGER.error("No entry_id in discovery info for AI Task platform")
        return
    
    # Get the config entry
    entries = hass.config_entries.async_entries(DOMAIN)
    entry = None
    for ent in entries:
        if ent.entry_id == entry_id:
            entry = ent
            break
    
    if entry is None:
        _LOGGER.error("Config entry %s not found for AI Task platform", entry_id)
        return
    
    # Check if AI Task is enabled
    if not entry.options.get(CONF_ENABLE_AI_TASK, True):
        _LOGGER.debug("AI Task entity disabled in options")
        return
    
    # Check if AI provider is configured
    if CONF_AI_PROVIDER not in entry.data:
        _LOGGER.error("No AI provider configured for AI Task entity")
        return
    
    # Create and add the AI Task entity
    entity = GLMAgentAITaskEntity(hass, entry)
    async_add_entities([entity], True)
    
    _LOGGER.info("AI Task entity added for GLM Agent HA: %s", entity.entity_id)