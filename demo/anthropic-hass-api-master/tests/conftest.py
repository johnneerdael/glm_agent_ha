"""Common fixtures for the Anthropic tests."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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

from tests.common import MockConfigEntry


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return the default mocked config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={CONF_API_KEY: "test-api-key"},
        options={
            CONF_PROMPT: DEFAULT_PROMPT,
            CONF_CONTROL_HA: DEFAULT_CONTROL_HA,
            CONF_RECOMMENDED_SETTINGS: DEFAULT_RECOMMENDED_SETTINGS,
            CONF_CHAT_MODEL: AnthropicModels.default(),
            CONF_MAX_TOKENS: DEFAULT_MAX_TOKENS,
            CONF_TEMPERATURE: DEFAULT_TEMPERATURE,
        },
    )


@pytest.fixture
def mock_setup_entry() -> AsyncMock:
    """Mock setting up a config entry."""
    with patch(
        "homeassistant.components.anthropic.async_setup_entry", return_value=True
    ) as mock_setup:
        yield mock_setup


@pytest.fixture
def mock_anthropic() -> MagicMock:
    """Return a mocked Anthropic client."""
    with patch("anthropic.Anthropic", autospec=True) as mock_client:
        client = mock_client.return_value
        message_response = MagicMock()
        message_response.content = [MagicMock(text="Test response from Claude")]
        client.messages.create = AsyncMock(return_value=message_response)
        yield client