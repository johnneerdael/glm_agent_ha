"""Conversation support for Anthropic."""
from __future__ import annotations

from homeassistant.components import assist_pipeline, conversation as ha_conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from custom_components.anthropic.conversation_agent import AnthropicAgent
from custom_components.anthropic.const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up conversation entities."""
    client = hass.data[DOMAIN][config_entry.entry_id]
    agent = AnthropicAgent(hass, config_entry, client)
    async_add_entities([agent])