"""Test the Anthropic integration initialization."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import requests

from homeassistant.components.anthropic.const import (
    CONF_CHAT_MODEL,
    CONF_CONTROL_HA,
    CONF_MAX_TOKENS,
    CONF_PROMPT,
    CONF_RECOMMENDED_SETTINGS,
    CONF_TEMPERATURE,
    DEFAULT_CONTROL_HA,
    DEFAULT_MAX_TOKENS,
    DEFAULT_PROMPT,
    DEFAULT_RECOMMENDED_SETTINGS,
    DEFAULT_TEMPERATURE,
    DOMAIN,
    AnthropicModels,
)
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.setup import async_setup_component

from tests.common import MockConfigEntry


async def test_setup_entry(hass: HomeAssistant) -> None:
    """Test setting up the integration."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_API_KEY: "test-api-key"},
        options={},
    )
    entry.add_to_hass(hass)

    with patch(
        "requests.post",
        return_value=MagicMock(
            status_code=200,
            json=MagicMock(return_value={"content": [{"text": "Test response"}]})
        ),
    ), patch(
        "homeassistant.components.anthropic.conversation.AnthropicAgent",
        return_value=MagicMock(),
    ), patch(
        "homeassistant.components.conversation.async_set_agent",
        return_value=None,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert DOMAIN in hass.data
    assert entry.entry_id in hass.data[DOMAIN]
    
    # Check that default options were set
    assert entry.options[CONF_PROMPT] == DEFAULT_PROMPT
    assert entry.options[CONF_CONTROL_HA] == DEFAULT_CONTROL_HA
    assert entry.options[CONF_RECOMMENDED_SETTINGS] == DEFAULT_RECOMMENDED_SETTINGS
    assert entry.options[CONF_CHAT_MODEL] == AnthropicModels.default()
    assert entry.options[CONF_MAX_TOKENS] == DEFAULT_MAX_TOKENS
    assert entry.options[CONF_TEMPERATURE] == DEFAULT_TEMPERATURE


async def test_setup_entry_fails(hass: HomeAssistant) -> None:
    """Test setting up the integration fails."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_API_KEY: "test-api-key"},
        options={},
    )
    entry.add_to_hass(hass)

    with patch(
        "requests.post",
        side_effect=Exception("Failed to initialize"),
    ):
        with pytest.raises(ConfigEntryNotReady):
            assert not await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()


async def test_unload_entry(hass: HomeAssistant) -> None:
    """Test unloading the integration."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_API_KEY: "test-api-key"},
        options={},
    )
    entry.add_to_hass(hass)

    with patch(
        "requests.post",
        return_value=MagicMock(
            status_code=200,
            json=MagicMock(return_value={"content": [{"text": "Test response"}]})
        ),
    ), patch(
        "homeassistant.components.anthropic.conversation.AnthropicAgent",
        return_value=MagicMock(),
    ), patch(
        "homeassistant.components.conversation.async_set_agent",
        return_value=None,
    ), patch(
        "homeassistant.components.conversation.async_unset_agent",
        return_value=None,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        
        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
        
        assert entry.entry_id not in hass.data[DOMAIN]