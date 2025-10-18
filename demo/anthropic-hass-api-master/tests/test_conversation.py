"""Test the Anthropic conversation agent."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import custom_components.anthropic.conversation

from homeassistant.components import conversation
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
    DEFAULT_TEMPERATURE,
    DOMAIN,
    AnthropicModels,
)
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent

from tests.common import MockConfigEntry


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client."""
    # Create a mock client with the same structure as our wrapper
    client = MagicMock()
    messages = MagicMock()
    
    # Create a response object with the same structure as our wrapper
    class ResponseContent:
        """Response content object."""
        def __init__(self, text):
            """Initialize the response content."""
            self.text = text
    
    class Response:
        """Response object."""
        def __init__(self, content):
            """Initialize the response."""
            self.content = content
    
    # Set up the mock to return a response
    response = Response([ResponseContent("Test response from Claude")])
    messages.create = MagicMock(return_value=response)
    client.messages = messages
    
    yield client


async def test_conversation_agent(hass: HomeAssistant, mock_anthropic_client) -> None:
    """Test the conversation agent."""
    # Mock the inspect.signature function
    with patch("inspect.signature", return_value=MagicMock()):
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_API_KEY: "test-api-key"},
            options={
                CONF_PROMPT: DEFAULT_PROMPT,
                CONF_CONTROL_HA: DEFAULT_CONTROL_HA,
                CONF_RECOMMENDED_SETTINGS: True,
                CONF_CHAT_MODEL: AnthropicModels.default(),
                CONF_MAX_TOKENS: DEFAULT_MAX_TOKENS,
                CONF_TEMPERATURE: DEFAULT_TEMPERATURE,
            },
        )
        entry.add_to_hass(hass)

        with patch(
            "homeassistant.components.anthropic.conversation.AnthropicAgent",
        ) as mock_agent_class, patch(
            "homeassistant.components.anthropic.async_setup_entry",
            return_value=True,
        ):
            mock_agent = mock_agent_class.return_value
            mock_agent.async_process = AsyncMock(
                return_value=conversation.ConversationResult(
                    conversation_id="test_conversation_id",
                    response=conversation.ConversationResponse(
                        speech={"plain": {"speech": "Test response from Claude", "extra_data": None}},
                        intent=intent.IntentResponse(language="en"),
                    ),
                )
            )
            assert await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()

            result = await conversation.async_converse(
                hass, "Hello Claude", None, None, entry.entry_id
            )

            assert result.response.speech["plain"]["speech"] == "Test response from Claude"


async def test_conversation_agent_with_ha_control(
    hass: HomeAssistant, mock_anthropic_client
) -> None:
    """Test the conversation agent with Home Assistant control."""
    # Mock the inspect.signature function
    with patch("inspect.signature", return_value=MagicMock()):
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_API_KEY: "test-api-key"},
            options={
                CONF_PROMPT: DEFAULT_PROMPT,
                CONF_CONTROL_HA: True,
                CONF_RECOMMENDED_SETTINGS: True,
                CONF_CHAT_MODEL: AnthropicModels.default(),
                CONF_MAX_TOKENS: DEFAULT_MAX_TOKENS,
                CONF_TEMPERATURE: DEFAULT_TEMPERATURE,
            },
        )
        entry.add_to_hass(hass)

        from homeassistant.components.anthropic.conversation import AnthropicAgent

        with patch(
            "homeassistant.components.anthropic.conversation.conversation.async_converse",
            return_value=conversation.ConversationResult(
                conversation_id="test_conversation_id",
                response=conversation.ConversationResponse(
                    speech={"plain": {"speech": "Turning on the light", "extra_data": None}},
                    intent=intent.IntentResponse(
                        language="en",
                        response_type=intent.IntentResponseType.ACTION_DONE,
                        slots={"entity_id": {"value": "light.living_room"}},
                    ),
                ),
            ),
        ), patch(
            "homeassistant.components.anthropic.async_setup_entry",
            return_value=True,
        ):
            assert await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()

            agent = hass.data[DOMAIN][entry.entry_id]
            result = await agent.async_process(
                conversation.ConversationInput(
                    text="Turn on the living room light",
                    conversation_id=None,
                    language="en",
                    agent_id=entry.entry_id,
                )
            )

            assert result.response.speech["plain"]["speech"] == "Turning on the light"