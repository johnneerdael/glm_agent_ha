"""Fixtures for AI Agent HA tests."""
import asyncio
from unittest.mock import patch

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component


@pytest.fixture
async def hass():
    """Return a Home Assistant instance for testing."""
    hass = HomeAssistant()
    hass.config.components.add("persistent_notification")
    
    # Start Home Assistant
    await hass.async_start()
    
    yield hass
    
    # Stop Home Assistant
    await hass.async_stop()


@pytest.fixture
def mock_agent():
    """Mock the AI Agent."""
    with patch("custom_components.ai_agent_ha.agent.AiAgentHaAgent") as mock:
        yield mock 