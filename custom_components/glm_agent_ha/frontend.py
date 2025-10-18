"""Frontend platform for GLM Agent HA integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .frontend_entity import GLMAgentFrontendEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up GLM Agent HA frontend platform."""

    _LOGGER.debug("Setting up GLM Agent HA frontend platform")

    # Create and add the frontend entity
    frontend_entity = GLMAgentFrontendEntity(hass, entry)
    async_add_entities([frontend_entity], True)

    _LOGGER.info("GLM Agent HA frontend entity registered successfully")