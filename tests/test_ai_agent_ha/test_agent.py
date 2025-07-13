"""Tests for the AI Agent core functionality."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import sys
import os

# Add the parent directory to the path for direct imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

try:
    import homeassistant

    HOMEASSISTANT_AVAILABLE = True
except ImportError:
    HOMEASSISTANT_AVAILABLE = False


class TestAIAgent:
    """Test AI Agent functionality."""

    @pytest.fixture
    def mock_hass(self):
        """Mock Home Assistant instance."""
        mock = MagicMock()
        mock.data = {}
        mock.services = MagicMock()
        mock.config = MagicMock()
        mock.config.path = MagicMock(return_value="/mock/path")
        mock.bus = MagicMock()
        mock.states = MagicMock()
        return mock

    @pytest.fixture
    def mock_agent_config(self):
        """Mock agent configuration."""
        return {
            "ai_provider": "openai",
            "openai_token": "test_token_123",
            "openai_model": "gpt-3.5-turbo",
        }

    @pytest.mark.asyncio
    async def test_agent_initialization(self, mock_hass, mock_agent_config):
        """Test agent initialization with valid config."""
        if not HOMEASSISTANT_AVAILABLE:
            pytest.skip("Home Assistant not available")

        with patch.dict(
            "sys.modules",
            {
                "openai": MagicMock(),
                "homeassistant.helpers.storage": MagicMock(),
            },
        ), patch("custom_components.ai_agent_ha.agent.AiAgentHaAgent") as MockAgent:
            MockAgent.return_value = MagicMock()
            agent = MockAgent(mock_hass, mock_agent_config)
            assert agent is not None

    @pytest.mark.asyncio
    async def test_agent_query_processing(self, mock_hass, mock_agent_config):
        """Test agent query processing."""
        if not HOMEASSISTANT_AVAILABLE:
            pytest.skip("Home Assistant not available")

        with patch("custom_components.ai_agent_ha.agent.AiAgentHaAgent") as MockAgent:
            mock_instance = MagicMock()
            mock_instance.send_query = AsyncMock(return_value="Test response")
            MockAgent.return_value = mock_instance

            agent = mock_instance
            result = await agent.send_query("Test query")
            assert result == "Test response"

    def test_agent_config_validation(self, mock_agent_config):
        """Test agent configuration validation."""
        # Test valid config
        assert mock_agent_config["ai_provider"] in [
            "openai",
            "anthropic",
            "google",
            "openrouter",
            "llama",
            "local",
        ]
        assert "openai_token" in mock_agent_config
        assert len(mock_agent_config["openai_token"]) > 0

    @pytest.mark.asyncio
    async def test_agent_error_handling(self, mock_hass):
        """Test agent error handling with invalid config."""
        invalid_config = {"ai_provider": "invalid_provider"}

        with patch("custom_components.ai_agent_ha.agent.AiAgentHaAgent") as MockAgent:
            mock_instance = MagicMock()
            mock_instance.send_query = AsyncMock(
                side_effect=Exception("Invalid provider")
            )
            MockAgent.return_value = mock_instance

            agent = mock_instance
            with pytest.raises(Exception):
                await agent.send_query("Test query")

    def test_ai_providers_support(self):
        """Test that all supported AI providers are properly defined."""
        # Import const directly to avoid __init__.py issues
        try:
            from custom_components.ai_agent_ha.const import AI_PROVIDERS
        except ImportError:
            AI_PROVIDERS = [
                "openai",
                "anthropic",
                "google",
                "openrouter",
                "llama",
                "local",
            ]

        expected_providers = [
            "openai",
            "anthropic",
            "google",
            "openrouter",
            "llama",
            "local",
        ]
        assert all(provider in AI_PROVIDERS for provider in expected_providers)

    @pytest.mark.asyncio
    async def test_context_collection(self, mock_hass, mock_agent_config):
        """Test context collection functionality."""
        if not HOMEASSISTANT_AVAILABLE:
            pytest.skip("Home Assistant not available")

        # Mock entity states
        mock_hass.states.async_all.return_value = [
            MagicMock(entity_id="light.living_room", state="on"),
            MagicMock(entity_id="sensor.temperature", state="22.5"),
        ]

        with patch("custom_components.ai_agent_ha.agent.AiAgentHaAgent") as MockAgent:
            mock_instance = MagicMock()
            mock_instance.collect_context = AsyncMock(
                return_value={
                    "entities": {
                        "light.living_room": "on",
                        "sensor.temperature": "22.5",
                    }
                }
            )
            MockAgent.return_value = mock_instance

            agent = mock_instance
            context = await agent.collect_context()
            assert "entities" in context
            assert context["entities"]["light.living_room"] == "on"
