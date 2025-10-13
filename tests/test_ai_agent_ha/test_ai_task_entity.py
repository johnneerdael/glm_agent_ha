"""Tests for GLM Agent HA AI Task entity."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.ai_task import GenDataTask, GenDataTaskResult
from homeassistant.core import HomeAssistant

from custom_components.glm_agent_ha.ai_task_entity import GLMAgentAITaskEntity
from custom_components.glm_agent_ha.const import (
    CONF_AI_PROVIDER,
    CONF_PLAN,
    PLAN_PRO,
)


@pytest.fixture
def hass():
    """Create a test Home Assistant instance."""
    return MagicMock(spec=HomeAssistant)


@pytest.fixture
def config_entry():
    """Create a test config entry."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.data = {
        CONF_AI_PROVIDER: "openai",
        "openai_token": "test_token",
        "models": {"openai": "GLM-4.6"},
        CONF_PLAN: PLAN_PRO,
    }
    entry.options = {
        "enable_mcp_integration": True,
        "enable_ai_task": True,
        "ha_base_url": "http://test.local:8123",
    }
    return entry


@pytest.fixture
def ai_task_entity(hass, config_entry):
    """Create a test AI Task entity."""
    with patch("custom_components.glm_agent_ha.ai_task_entity.AiAgentHaAgent"):
        entity = GLMAgentAITaskEntity(hass, config_entry)
        return entity


class TestGLMAgentAITaskEntity:
    """Test the GLMAgentAITaskEntity class."""

    def test_entity_properties(self, ai_task_entity):
        """Test entity properties."""
        assert ai_task_entity.name == "GLM Agent AI Task"
        assert ai_task_entity.unique_id == "test_entry_id_ai_task"
        assert ai_task_entity.available is True
        assert hasattr(ai_task_entity, "_attr_supported_features")

    def test_mcp_support_check(self, ai_task_entity):
        """Test MCP support checking."""
        # Test with MCP manager available
        ai_task_entity._mcp_manager = MagicMock()
        ai_task_entity._entry.options["enable_mcp_integration"] = True
        assert ai_task_entity._has_mcp_support() is True

        # Test with MCP manager disabled
        ai_task_entity._mcp_manager = MagicMock()
        ai_task_entity._entry.options["enable_mcp_integration"] = False
        assert ai_task_entity._has_mcp_support() is False

        # Test without MCP manager
        ai_task_entity._mcp_manager = None
        assert ai_task_entity._has_mcp_support() is False

    @pytest.mark.asyncio
    async def test_download_and_save_media(self, ai_task_entity):
        """Test media download and save functionality."""
        # Mock the media source resolution
        mock_media = MagicMock()
        mock_media.url = "http://test.url/image.jpg"
        
        with patch("custom_components.glm_agent_ha.ai_task_entity.async_resolve_media") as mock_resolve:
            mock_resolve.return_value = mock_media
            
            # Mock the HTTP response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.read.return_value = b"test_image_data"
            
            mock_session = AsyncMock()
            mock_session.get.return_value.__aenter__.return_value = mock_response
            
            ai_task_entity.hass.helpers.aiohttp_client.async_get_clientsession.return_value = mock_session
            
            # Mock file operations
            with patch("builtins.open", create=True) as mock_open, \
                 patch("os.makedirs") as mock_makedirs, \
                 patch("os.path.join") as mock_join:
                
                mock_join.return_value = "/config/www/test_image.jpg"
                mock_file = MagicMock()
                mock_open.return_value.__enter__.return_value = mock_file
                
                # Test the method
                url = await ai_task_entity._download_and_save_media("media:test")
                
                # Verify the result
                assert url == "http://test.local:8123/local/test_image.jpg"
                
                # Verify the function calls
                mock_resolve.assert_called_once_with(ai_task_entity.hass, "media:test", None)
                mock_session.get.assert_called_once_with("http://test.url/image.jpg")
                mock_makedirs.assert_called_once()
                mock_open.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_media_with_mcp(self, ai_task_entity):
        """Test MCP media analysis."""
        # Setup MCP manager
        mock_mcp_manager = AsyncMock()
        mock_mcp_manager.analyze_image.return_value = "Test image analysis result"
        ai_task_entity._mcp_manager = mock_mcp_manager
        
        # Test the method
        result = await ai_task_entity._analyze_media_with_mcp("http://test.url/image.jpg")
        
        # Verify the result
        assert result == "Test image analysis result"
        mock_mcp_manager.analyze_image.assert_called_once_with(
            "http://test.url/image.jpg",
            prompt="Describe this image in detail for AI analysis"
        )

    @pytest.mark.asyncio
    async def test_analyze_media_with_mcp_error(self, ai_task_entity):
        """Test MCP media analysis error handling."""
        # Setup MCP manager with error
        mock_mcp_manager = AsyncMock()
        mock_mcp_manager.analyze_image.side_effect = Exception("MCP Error")
        ai_task_entity._mcp_manager = mock_mcp_manager
        
        # Test the method raises error
        with pytest.raises(Exception, match="MCP Error"):
            await ai_task_entity._analyze_media_with_mcp("http://test.url/image.jpg")

    @pytest.mark.asyncio
    async def test_async_generate_data_without_attachments(self, ai_task_entity):
        """Test generate data without attachments."""
        # Setup agent
        mock_agent = AsyncMock()
        mock_agent.process_query.return_value = {"result": "test_data"}
        ai_task_entity._agent = mock_agent
        
        # Create test task
        task = GenDataTask(
            task_name="test_task",
            instructions="Test instructions",
            structure=None,
            attachments=None,
        )
        
        mock_chat_log = MagicMock()
        mock_chat_log.conversation_id = "test_conv_id"
        
        # Test the method
        result = await ai_task_entity._async_generate_data(task, mock_chat_log)
        
        # Verify the result
        assert isinstance(result, GenDataTaskResult)
        assert result.conversation_id == "test_conv_id"
        assert result.data == {"result": "test_data"}
        
        # Verify agent was called
        mock_agent.process_query.assert_called_once_with(
            prompt="Test instructions",
            structure=None,
            chat_log=mock_chat_log
        )

    @pytest.mark.asyncio
    async def test_async_generate_data_with_attachments_mcp_success(self, ai_task_entity):
        """Test generate data with attachments and MCP success."""
        # Setup agent
        mock_agent = AsyncMock()
        mock_agent.process_query.return_value = {"result": "test_data_with_analysis"}
        ai_task_entity._agent = mock_agent
        
        # Setup MCP manager
        mock_mcp_manager = AsyncMock()
        mock_mcp_manager.analyze_image.return_value = "Image shows a person walking"
        ai_task_entity._mcp_manager = mock_mcp_manager
        
        # Mock media download
        with patch.object(ai_task_entity, "_download_and_save_media") as mock_download:
            mock_download.return_value = "http://test.local:8123/local/test_image.jpg"
            
            # Create test task with attachment
            mock_attachment = MagicMock()
            mock_attachment.media_content_id = "media:camera.test"
            
            task = GenDataTask(
                task_name="test_task",
                instructions="Analyze this image",
                structure=None,
                attachments=[mock_attachment],
            )
            
            mock_chat_log = MagicMock()
            mock_chat_log.conversation_id = "test_conv_id"
            
            # Test the method
            result = await ai_task_entity._async_generate_data(task, mock_chat_log)
            
            # Verify the result
            assert isinstance(result, GenDataTaskResult)
            assert result.conversation_id == "test_conv_id"
            assert result.data == {"result": "test_data_with_analysis"}
            
            # Verify MCP was called
            mock_mcp_manager.analyze_image.assert_called_once_with(
                "http://test.local:8123/local/test_image.jpg",
                prompt="Describe this image in detail for AI analysis"
            )
            
            # Verify enhanced instructions include attachment analysis
            call_args = mock_agent.process_query.call_args
            enhanced_instructions = call_args[1]["prompt"]
            assert "Image shows a person walking" in enhanced_instructions
            assert "Context from attached media:" in enhanced_instructions

    @pytest.mark.asyncio
    async def test_async_generate_data_with_attachments_mcp_error(self, ai_task_entity):
        """Test generate data with attachments and MCP error handling."""
        # Setup agent
        mock_agent = AsyncMock()
        mock_agent.process_query.return_value = {"result": "test_data_without_analysis"}
        ai_task_entity._agent = mock_agent
        
        # Setup MCP manager with error
        mock_mcp_manager = AsyncMock()
        mock_mcp_manager.analyze_image.side_effect = Exception("MCP Error")
        ai_task_entity._mcp_manager = mock_mcp_manager
        
        # Mock media download
        with patch.object(ai_task_entity, "_download_and_save_media") as mock_download:
            mock_download.return_value = "http://test.local:8123/local/test_image.jpg"
            
            # Create test task with attachment
            mock_attachment = MagicMock()
            mock_attachment.media_content_id = "media:camera.test"
            
            task = GenDataTask(
                task_name="test_task",
                instructions="Analyze this image",
                structure=None,
                attachments=[mock_attachment],
            )
            
            mock_chat_log = MagicMock()
            mock_chat_log.conversation_id = "test_conv_id"
            
            # Test the method - should not raise error
            result = await ai_task_entity._async_generate_data(task, mock_chat_log)
            
            # Verify the result
            assert isinstance(result, GenDataTaskResult)
            assert result.conversation_id == "test_conv_id"
            assert result.data == {"result": "test_data_without_analysis"}
            
            # Verify enhanced instructions include error message
            call_args = mock_agent.process_query.call_args
            enhanced_instructions = call_args[1]["prompt"]
            assert "Unable to analyze media" in enhanced_instructions
            assert "MCP Error" in enhanced_instructions

    @pytest.mark.asyncio
    async def test_async_generate_data_with_attachments_no_mcp(self, ai_task_entity):
        """Test generate data with attachments but no MCP support."""
        # Setup agent
        mock_agent = AsyncMock()
        mock_agent.process_query.return_value = {"result": "test_data_no_mcp"}
        ai_task_entity._agent = mock_agent
        
        # Disable MCP support
        ai_task_entity._mcp_manager = None
        
        # Create test task with attachment
        mock_attachment = MagicMock()
        mock_attachment.media_content_id = "media:camera.test"
        
        task = GenDataTask(
            task_name="test_task",
            instructions="Analyze this image",
            structure=None,
            attachments=[mock_attachment],
        )
        
        mock_chat_log = MagicMock()
        mock_chat_log.conversation_id = "test_conv_id"
        
        # Test the method
        result = await ai_task_entity._async_generate_data(task, mock_chat_log)
        
        # Verify the result
        assert isinstance(result, GenDataTaskResult)
        assert result.conversation_id == "test_conv_id"
        assert result.data == {"result": "test_data_no_mcp"}
        
        # Verify agent was called with original instructions (no attachment analysis)
        call_args = mock_agent.process_query.call_args
        enhanced_instructions = call_args[1]["prompt"]
        assert enhanced_instructions == "Analyze this image"

    @pytest.mark.asyncio
    async def test_async_generate_data_agent_error(self, ai_task_entity):
        """Test generate data with agent error."""
        # Setup agent with error
        mock_agent = AsyncMock()
        mock_agent.process_query.side_effect = Exception("Agent Error")
        ai_task_entity._agent = mock_agent
        
        # Create test task
        task = GenDataTask(
            task_name="test_task",
            instructions="Test instructions",
            structure=None,
            attachments=None,
        )
        
        mock_chat_log = MagicMock()
        mock_chat_log.conversation_id = "test_conv_id"
        
        # Test the method raises error
        with pytest.raises(Exception, match="Agent Error"):
            await ai_task_entity._async_generate_data(task, mock_chat_log)

    def test_device_info(self, ai_task_entity):
        """Test device info."""
        device_info = ai_task_entity.device_info
        assert device_info is not None
        assert device_info["identifiers"] == {("glm_agent_ha", "test_entry_id")}
        assert device_info["name"] == "GLM Agent HA"
        assert device_info["manufacturer"] == "GLM Agent HA"
        assert device_info["model"] == "pro"

    def test_entity_id_property(self, ai_task_entity):
        """Test entity_id property."""
        # The entity_id should be set by the platform
        assert not hasattr(ai_task_entity, "entity_id")

    def test_has_entity_name_property(self, ai_task_entity):
        """Test has_entity_name property."""
        assert ai_task_entity.has_entity_name is True