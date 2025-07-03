"""Test for AI Agent HA setup."""
from unittest.mock import patch, MagicMock, AsyncMock
import pytest
import sys
import os

# Add the parent directory to the path for direct imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from homeassistant.core import HomeAssistant
    from homeassistant.setup import async_setup_component
    from homeassistant.config_entries import ConfigEntry
    HOMEASSISTANT_AVAILABLE = True
except ImportError:
    HOMEASSISTANT_AVAILABLE = False
    HomeAssistant = MagicMock
    async_setup_component = MagicMock
    ConfigEntry = MagicMock

# Import const directly to avoid __init__.py issues
try:
    from custom_components.ai_agent_ha.const import DOMAIN
except ImportError:
    # Fallback for local testing
    DOMAIN = "ai_agent_ha"


@pytest.mark.asyncio
@pytest.mark.skipif(not HOMEASSISTANT_AVAILABLE, reason="Home Assistant not available")
async def test_async_setup():
    """Test the basic async_setup function."""
    # This is a very basic test that just checks if the function exists and returns True
    if HOMEASSISTANT_AVAILABLE:
        # Mock the required modules properly
        with patch('homeassistant.components.frontend.async_register_built_in_panel'), \
             patch('homeassistant.components.http.StaticPathConfig'), \
             patch('homeassistant.helpers.config_validation.config_entry_only_config_schema'), \
             patch('voluptuous.Schema'):
            
            from custom_components.ai_agent_ha import async_setup
            
            mock_hass = MagicMock()
            mock_config = MagicMock()
            
            result = await async_setup(mock_hass, mock_config)
            assert result is True


@pytest.mark.asyncio
@pytest.mark.skipif(not HOMEASSISTANT_AVAILABLE, reason="Home Assistant not available")
async def test_setup_entry():
    """Test setting up an entry.""" 
    # Mock all the imports at the module level
    with patch('homeassistant.components.frontend.async_register_built_in_panel'), \
         patch('homeassistant.components.http.StaticPathConfig'), \
         patch('homeassistant.helpers.config_validation.config_entry_only_config_schema'), \
         patch('homeassistant.exceptions.ConfigEntryNotReady'), \
         patch('voluptuous.Schema'), \
         patch('custom_components.ai_agent_ha.agent.AiAgentHaAgent') as mock_agent:
        
        from custom_components.ai_agent_ha import async_setup_entry
        
        # Create mock hass and entry
        mock_hass = MagicMock()
        mock_hass.data = {}
        mock_hass.services = MagicMock()
        mock_hass.http = MagicMock()
        mock_hass.http.async_register_static_paths = AsyncMock()
        mock_hass.config = MagicMock()
        mock_hass.config.path = MagicMock(return_value="/mock/path")
        
        mock_entry = MagicMock()
        mock_entry.version = 1
        mock_entry.data = {
            "ai_provider": "openai",
            "openai_token": "fake_token"
        }
        
        # The function should return True
        result = await async_setup_entry(mock_hass, mock_entry)
        assert result is True
        
        # Verify the agent was created
        mock_agent.assert_called_once() 