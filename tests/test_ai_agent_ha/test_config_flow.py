"""Tests for the configuration flow."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the parent directory to the path for direct imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

try:
    from homeassistant import config_entries
    from homeassistant.core import HomeAssistant
    from homeassistant.data_entry_flow import FlowResultType

    HOMEASSISTANT_AVAILABLE = True
except ImportError:
    HOMEASSISTANT_AVAILABLE = False
    config_entries = MagicMock()
    HomeAssistant = MagicMock
    FlowResultType = MagicMock()


class TestConfigFlow:
    """Test the config flow."""

    @pytest.fixture
    def mock_hass(self):
        """Mock Home Assistant instance."""
        mock = MagicMock()
        mock.data = {}
        mock.config_entries = MagicMock()
        return mock

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not HOMEASSISTANT_AVAILABLE, reason="Home Assistant not available"
    )
    async def test_flow_init(self, mock_hass):
        """Test the initial flow step."""
        with patch.dict(
            "sys.modules",
            {
                "homeassistant.helpers.config_validation": MagicMock(),
                "voluptuous": MagicMock(),
            },
        ):
            from custom_components.ai_agent_ha.config_flow import AiAgentHaConfigFlow

            flow = AiAgentHaConfigFlow()
            flow.hass = mock_hass

            result = await flow.async_step_user()
            assert result["type"] == "form"
            assert result["step_id"] == "user"

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not HOMEASSISTANT_AVAILABLE, reason="Home Assistant not available"
    )
    async def test_flow_openai_config(self, mock_hass):
        """Test OpenAI configuration flow."""
        with patch.dict(
            "sys.modules",
            {
                "homeassistant.helpers.config_validation": MagicMock(),
                "voluptuous": MagicMock(),
            },
        ):
            from custom_components.ai_agent_ha.config_flow import AiAgentHaConfigFlow

            flow = AiAgentHaConfigFlow()
            flow.hass = mock_hass

            # Test initial step
            result = await flow.async_step_user({"ai_provider": "openai"})
            assert result["type"] == "form"
            assert result["step_id"] == "openai"

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not HOMEASSISTANT_AVAILABLE, reason="Home Assistant not available"
    )
    async def test_flow_validation_success(self, mock_hass):
        """Test successful validation and entry creation."""
        with patch.dict(
            "sys.modules",
            {
                "homeassistant.helpers.config_validation": MagicMock(),
                "voluptuous": MagicMock(),
                "openai": MagicMock(),
            },
        ), patch(
            "custom_components.ai_agent_ha.config_flow.validate_openai_config"
        ) as mock_validate:

            mock_validate.return_value = True

            from custom_components.ai_agent_ha.config_flow import AiAgentHaConfigFlow

            flow = AiAgentHaConfigFlow()
            flow.hass = mock_hass

            # Mock the async_create_entry method
            flow.async_create_entry = Mock(return_value={"type": "create_entry"})

            result = await flow.async_step_openai(
                {"openai_token": "valid_token", "openai_model": "gpt-3.5-turbo"}
            )

            # Verify the flow completed successfully
            mock_validate.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not HOMEASSISTANT_AVAILABLE, reason="Home Assistant not available"
    )
    async def test_flow_validation_error(self, mock_hass):
        """Test validation error handling."""
        with patch.dict(
            "sys.modules",
            {
                "homeassistant.helpers.config_validation": MagicMock(),
                "voluptuous": MagicMock(),
                "openai": MagicMock(),
            },
        ), patch(
            "custom_components.ai_agent_ha.config_flow.validate_openai_config"
        ) as mock_validate:

            mock_validate.side_effect = Exception("Invalid token")

            from custom_components.ai_agent_ha.config_flow import AiAgentHaConfigFlow

            flow = AiAgentHaConfigFlow()
            flow.hass = mock_hass

            result = await flow.async_step_openai(
                {"openai_token": "invalid_token", "openai_model": "gpt-3.5-turbo"}
            )

            assert result["type"] == "form"
            assert "errors" in result

    def test_config_flow_constants(self):
        """Test config flow constants are properly defined."""
        try:
            from custom_components.ai_agent_ha.config_flow import AiAgentHaConfigFlow

            assert hasattr(AiAgentHaConfigFlow, "VERSION")
            assert AiAgentHaConfigFlow.VERSION == 1
        except ImportError:
            # Skip if not available
            pass

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not HOMEASSISTANT_AVAILABLE, reason="Home Assistant not available"
    )
    async def test_anthropic_config_flow(self, mock_hass):
        """Test Anthropic configuration flow."""
        with patch.dict(
            "sys.modules",
            {
                "homeassistant.helpers.config_validation": MagicMock(),
                "voluptuous": MagicMock(),
            },
        ):
            from custom_components.ai_agent_ha.config_flow import AiAgentHaConfigFlow

            flow = AiAgentHaConfigFlow()
            flow.hass = mock_hass

            # Test Anthropic provider selection
            result = await flow.async_step_user({"ai_provider": "anthropic"})
            assert result["type"] == "form"
            assert result["step_id"] == "anthropic"

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not HOMEASSISTANT_AVAILABLE, reason="Home Assistant not available"
    )
    async def test_google_config_flow(self, mock_hass):
        """Test Google configuration flow."""
        with patch.dict(
            "sys.modules",
            {
                "homeassistant.helpers.config_validation": MagicMock(),
                "voluptuous": MagicMock(),
            },
        ):
            from custom_components.ai_agent_ha.config_flow import AiAgentHaConfigFlow

            flow = AiAgentHaConfigFlow()
            flow.hass = mock_hass

            # Test Google provider selection
            result = await flow.async_step_user({"ai_provider": "google"})
            assert result["type"] == "form"
            assert result["step_id"] == "google"
