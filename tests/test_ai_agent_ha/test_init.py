"""Test for AI Agent HA setup."""
from unittest.mock import patch, MagicMock
import pytest

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.ai_agent_ha.const import DOMAIN


@pytest.mark.asyncio
async def test_setup(hass: HomeAssistant):
    """Test the component setup."""
    # Test the setup function returns true
    with patch("custom_components.ai_agent_ha.async_setup_entry", return_value=True):
        assert await async_setup_component(hass, DOMAIN, {})
        
    # Test that we can call the services
    assert hass.services.has_service(DOMAIN, "query")


@pytest.mark.asyncio
async def test_setup_entry(hass: HomeAssistant):
    """Test setting up an entry."""
    from custom_components.ai_agent_ha import async_setup_entry
    
    entry = MagicMock()
    entry.data = {
        "ai_provider": "test_provider",
        "test_provider_token": "fake_token"
    }
    
    # Mock the agent creation
    with patch("custom_components.ai_agent_ha.AiAgentHaAgent"):
        # Call the setup entry function
        assert await async_setup_entry(hass, entry) 