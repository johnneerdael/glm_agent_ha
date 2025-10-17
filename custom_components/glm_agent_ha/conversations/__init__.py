"""GLM Agent HA conversation integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from ..llm_integration import GLMConversationAgent
from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_conversation(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up GLM Agent HA conversation."""
    try:
        # Check if GLM Agent HA is loaded
        if DOMAIN not in hass.data:
            _LOGGER.warning("GLM Agent HA not loaded, cannot set up conversation")
            return False

        # Get the first available config entry
        entries = hass.config_entries.async_entries(DOMAIN)
        if not entries:
            _LOGGER.warning("No GLM Agent HA config entry found")
            return False

        entry = entries[0]
        config_data = dict(entry.data)

        # Create conversation agent
        agent = GLMConversationAgent(hass, config_data, entry.entry_id)

        # Register conversation agent
        hass.data.setdefault("conversation_agents", {})
        hass.data["conversation_agents"][DOMAIN] = agent

        _LOGGER.info("GLM Agent HA conversation agent registered")
        return True

    except Exception as e:
        _LOGGER.error("Error setting up GLM Agent HA conversation: %s", e)
        return False