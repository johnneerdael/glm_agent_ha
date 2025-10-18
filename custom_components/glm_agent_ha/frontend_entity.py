"""Frontend entity for GLM Agent HA integration.

This module provides a simple entity to register the frontend device
and ensure proper separation between frontend and services devices.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    FRONTEND_DEVICE_IDENTIFIERS,
    FRONTEND_DEVICE_NAME,
)

_LOGGER = logging.getLogger(__name__)


class GLMAgentFrontendEntity(Entity):
    """GLM Agent Frontend Entity for device registration.

    This entity provides a minimal implementation to ensure the frontend
    device is properly registered in Home Assistant's device registry.
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the GLM Agent frontend entity."""
        self.hass = hass
        self.entry = entry

        # Entity attributes
        self._attr_has_entity_name = True
        self._attr_name = "Frontend Panel"
        self._attr_unique_id = f"{entry.entry_id}_frontend"
        self._attr_should_poll = False
        self._attr_available = True

        # Use frontend device info from main module if available, otherwise create it
        if (DOMAIN in hass.data and
            "frontend_device_info" in hass.data[DOMAIN]):
            self._attr_device_info = hass.data[DOMAIN]["frontend_device_info"]
        else:
            # Fallback device info for proper integration - use frontend device
            self._attr_device_info = dr.DeviceInfo(
                identifiers={(DOMAIN, f"{FRONTEND_DEVICE_IDENTIFIERS}_{entry.entry_id}")},
                name=FRONTEND_DEVICE_NAME,
                manufacturer="Zhipu AI",
                model="GLM Agent Frontend",
                entry_type=dr.DeviceEntryType.SERVICE,
            )

    @property
    def state(self) -> str:
        """Return the entity state."""
        return "ready"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        return {
            "integration_type": "frontend",
            "panel_registered": True,
            "device_type": "frontend",
            "supported_features": ["visual_interface", "dashboard", "control_panel"],
        }

    async def async_added_to_hass(self) -> None:
        """When entity is added to Home Assistant."""
        await super().async_added_to_hass()
        _LOGGER.info("GLM Agent frontend entity added to Home Assistant")

    async def async_will_remove_from_hass(self) -> None:
        """When entity will be removed from Home Assistant."""
        await super().async_will_remove_from_hass()
        _LOGGER.info("GLM Agent frontend entity removed from Home Assistant")