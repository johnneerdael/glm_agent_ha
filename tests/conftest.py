"""Fixtures for AI Agent HA tests."""

import asyncio
import json
import os
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Any, Dict, Generator

import pytest
import pytest_asyncio

try:
    from homeassistant.core import HomeAssistant
    from homeassistant.setup import async_setup_component
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.helpers.entity_registry import EntityRegistry
    from homeassistant.helpers.service_registry import ServiceRegistry

    HOMEASSISTANT_AVAILABLE = True
except ImportError:
    HOMEASSISTANT_AVAILABLE = False
    # Mock Home Assistant classes for local testing
    HomeAssistant = MagicMock
    async_setup_component = MagicMock
    ConfigEntry = MagicMock
    EntityRegistry = MagicMock
    ServiceRegistry = MagicMock

from custom_components.glm_agent_ha.const import (
    CONF_OPENAI_API_KEY,
    CONF_MODEL,
    CONF_PLAN,
    CONF_ENABLE_CONTEXT_SERVICES,
    CONF_ENABLE_MCP_INTEGRATION,
    DEFAULT_MODEL,
    DEFAULT_PLAN,
    DOMAIN,
)

# Test data constants
TEST_API_KEY = "test-api-key-12345"
TEST_CONFIG = {
    CONF_OPENAI_API_KEY: TEST_API_KEY,
    CONF_MODEL: DEFAULT_MODEL,
    CONF_PLAN: DEFAULT_PLAN,
    CONF_ENABLE_CONTEXT_SERVICES: True,
    CONF_ENABLE_MCP_INTEGRATION: False,
}

TEST_CONFIG_LITE = {
    CONF_OPENAI_API_KEY: TEST_API_KEY,
    CONF_MODEL: "gpt-3.5-turbo",
    CONF_PLAN: "lite",
    CONF_ENABLE_CONTEXT_SERVICES: False,
    CONF_ENABLE_MCP_INTEGRATION: False,
}

TEST_CONFIG_PRO = {
    CONF_OPENAI_API_KEY: TEST_API_KEY,
    CONF_MODEL: "gpt-4",
    CONF_PLAN: "pro",
    CONF_ENABLE_CONTEXT_SERVICES: True,
    CONF_ENABLE_MCP_INTEGRATION: True,
}

# Mock responses
MOCK_AI_RESPONSE = {
    "choices": [
        {
            "message": {
                "content": "Test AI response about Home Assistant automation"
            }
        }
    ],
    "usage": {
        "prompt_tokens": 10,
        "completion_tokens": 5,
        "total_tokens": 15
    }
}

MOCK_AUTOMATION_RESPONSE = """
{
  "automation": {
    "id": "test_automation",
    "alias": "Test Automation",
    "description": "Test automation created during testing",
    "trigger": [
      {
        "platform": "state",
        "entity_id": "switch.test_switch"
      }
    ],
    "action": [
      {
        "service": "light.turn_on",
        "target": {
          "entity_id": "light.test_light"
        }
      }
    ],
    "mode": "single"
  }
}
"""

MOCK_DASHBOARD_RESPONSE = """
{
  "dashboard": {
    "title": "Test Dashboard",
    "views": [
      {
        "title": "Test View",
        "cards": [
          {
            "type": "entities",
            "entities": ["light.test_light", "switch.test_switch"]
          }
        ]
      }
    ]
  }
}
"""


@pytest.fixture
async def hass():
    """Return a Home Assistant instance for testing."""
    if not HOMEASSISTANT_AVAILABLE:
        # Return a mock for local testing
        mock_hass = MagicMock()
        mock_hass.data = {}
        mock_hass.services = MagicMock()
        mock_hass.config = MagicMock()
        mock_hass.config.components = set()
        mock_hass.async_add_job = AsyncMock()
        mock_hass.async_create_task = AsyncMock()
        mock_hass.async_add_executor_job = AsyncMock()
        mock_hass.bus = MagicMock()
        mock_hass.bus.async_listen = MagicMock()
        mock_hass.bus.async_fire = MagicMock()
        mock_hass.states = MagicMock()
        mock_hass.states.async_get = MagicMock(return_value=None)
        mock_hass.states.async_set = MagicMock()
        yield mock_hass
        return

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
    with patch("custom_components.glm_agent_ha.agent.AiAgentHaAgent") as mock:
        yield mock


@pytest.fixture
def mock_config_entry() -> ConfigEntry:
    """Create a mock config entry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.data = dict(TEST_CONFIG)
    entry.options = {}
    entry.title = "GLM Agent HA"
    entry.domain = DOMAIN
    entry.source = "user"
    entry.unique_id = "test_unique_id"
    return entry


@pytest.fixture
def mock_config_entry_lite() -> ConfigEntry:
    """Create a mock config entry for lite plan."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_lite"
    entry.data = dict(TEST_CONFIG_LITE)
    entry.options = {}
    entry.title = "GLM Agent HA Lite"
    entry.domain = DOMAIN
    entry.source = "user"
    entry.unique_id = "test_unique_lite"
    return entry


@pytest.fixture
def mock_config_entry_pro() -> ConfigEntry:
    """Create a mock config entry for pro plan."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_pro"
    entry.data = dict(TEST_CONFIG_PRO)
    entry.options = {}
    entry.title = "GLM Agent HA Pro"
    entry.domain = DOMAIN
    entry.source = "user"
    entry.unique_id = "test_unique_pro"
    return entry


@pytest.fixture
def mock_aiohttp_session():
    """Mock aiohttp session for API calls."""
    session = AsyncMock()
    response = AsyncMock()
    response.status = 200
    response.json = AsyncMock(return_value=MOCK_AI_RESPONSE)
    response.text = AsyncMock(return_value=json.dumps(MOCK_AI_RESPONSE))
    session.post = AsyncMock(return_value=response)
    session.get = AsyncMock(return_value=response)
    session.close = AsyncMock()
    return session


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    client = AsyncMock()
    client.chat.completions.create = AsyncMock(return_value=MagicMock(**MOCK_AI_RESPONSE))
    return client


@pytest.fixture
def sample_entities_data():
    """Sample entities data for testing."""
    return {
        "light.test_light": {
            "entity_id": "light.test_light",
            "friendly_name": "Test Light",
            "state": "off",
            "attributes": {
                "brightness": 0,
                "supported_color_modes": ["brightness"],
                "icon": "mdi:lightbulb"
            }
        },
        "switch.test_switch": {
            "entity_id": "switch.test_switch",
            "friendly_name": "Test Switch",
            "state": "off",
            "attributes": {
                "icon": "mdi:power"
            }
        },
        "sensor.test_temperature": {
            "entity_id": "sensor.test_temperature",
            "friendly_name": "Test Temperature",
            "state": "22.5",
            "attributes": {
                "unit_of_measurement": "°C",
                "device_class": "temperature"
            }
        }
    }


@pytest.fixture
def sample_areas_data():
    """Sample areas data for testing."""
    return {
        "living_room": {
            "area_id": "living_room",
            "name": "Living Room",
            "picture": None,
            "entities": ["light.test_light", "switch.test_switch"]
        },
        "kitchen": {
            "area_id": "kitchen",
            "name": "Kitchen",
            "picture": None,
            "entities": ["sensor.test_temperature"]
        }
    }


@pytest.fixture
def sample_devices_data():
    """Sample devices data for testing."""
    return {
        "test_light_device": {
            "device_id": "test_light_device",
            "name": "Test Light Device",
            "model": "Smart Bulb v2",
            "manufacturer": "Test Company",
            "area_id": "living_room",
            "entities": ["light.test_light"]
        }
    }


@pytest.fixture
def sample_automation_request():
    """Sample automation request for testing."""
    return {
        "prompt": "Turn on the living room light when the switch is turned on",
        "name": "Living Room Automation",
        "description": "Automation to control living room lighting"
    }


@pytest.fixture
def sample_dashboard_request():
    """Sample dashboard request for testing."""
    return {
        "prompt": "Create a dashboard for the living room",
        "name": "Living Room Dashboard",
        "type": "room_based",
        "area": "living_room"
    }


@pytest.fixture
def sample_conversation_history():
    """Sample conversation history for testing."""
    return [
        {
            "role": "user",
            "content": "Hello, can you help me with Home Assistant?",
            "timestamp": "2025-01-14T10:00:00Z"
        },
        {
            "role": "assistant",
            "content": "Hello! I'd be happy to help you with Home Assistant. What would you like to do?",
            "timestamp": "2025-01-14T10:00:05Z"
        }
    ]


# Helper functions for tests
def assert_service_call(hass: HomeAssistant, service: str, called: bool = True, **kwargs):
    """Assert that a service was called with specific parameters."""
    service_calls = hass.services.async_call.call_args_list
    if called:
        assert len(service_calls) > 0, f"Service {service} was not called"
        if kwargs:
            # Check if any call matches the expected parameters
            for call in service_calls:
                if (call[0][0] == DOMAIN and
                    call[0][1] == service.split('.')[-1] and
                    all(k in call[1] and call[1][k] == v for k, v in kwargs.items())):
                    return
            assert False, f"Service {service} was called but not with expected parameters: {kwargs}"
    else:
        # Check that no call matches the service
        for call in service_calls:
            if call[0][0] == DOMAIN and call[0][1] == service.split('.')[-1]:
                assert False, f"Service {service} was called but should not have been"


def assert_log_entry(logs: list, level: str, category: str, message_contains: str = None):
    """Assert that a log entry with specific characteristics exists."""
    for log in logs:
        if (log.get('level') == level and
            log.get('category') == category and
            (message_contains is None or message_contains in log.get('message', ''))):
            return
    assert False, f"No log entry found with level={level}, category={category}, message_contains={message_contains}"


def create_mock_request(data: Dict[str, Any]) -> MagicMock:
    """Create a mock service request."""
    request = MagicMock()
    request.data = data
    request.context = MagicMock()
    request.context.user_id = "test_user"
    request.context.request_id = "test_request_123"
    return request


async def wait_for_service_calls(hass: HomeAssistant, timeout: float = 1.0):
    """Wait for service calls to complete."""
    await asyncio.sleep(timeout)
    if hasattr(hass, 'async_block_till_done'):
        await hass.async_block_till_done()


# Pytest configuration
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "security: Security tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "slow: Slow running tests")


@pytest.fixture(scope="session", autouse=True)
def configure_logging():
    """Configure logging for tests."""
    import logging
    logging.basicConfig(level=logging.DEBUG)

    # Reduce noise from some libraries during testing
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
