"""Fixtures for AI Agent HA tests."""
import asyncio
from unittest.mock import patch

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component


@pytest.fixture
def hass(event_loop):
    """Return a Home Assistant instance for testing."""
    hass = HomeAssistant()
    hass.config.components.add("persistent_notification")

    async def async_start_ha():
        await hass.async_start()
        return hass

    hass = event_loop.run_until_complete(async_start_ha())

    yield hass

    event_loop.run_until_complete(hass.async_stop())


@pytest.fixture
def mock_agent():
    """Mock the AI Agent."""
    with patch("custom_components.ai_agent_ha.agent.AiAgentHaAgent") as mock:
        yield mock 