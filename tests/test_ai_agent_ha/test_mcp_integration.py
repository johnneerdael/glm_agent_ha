"""Test MCP integration for GLM AI Agent HA integration."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.glm_agent_ha.mcp_integration import MCPIntegrationManager
from custom_components.glm_agent_ha.agent import AiAgentHaAgent


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock()
    hass.config.path.return_value = "/config"
    return hass


@pytest.fixture
def lite_config():
    """Create a Lite plan configuration."""
    return {
        "ai_provider": "openai",
        "openai_token": "test_token_12345678901234567890",
        "plan": "lite",
        "models": {"openai": "GLM-4.5-air"},
        "mcp_servers": [],
        "plan_capabilities": {
            "mcp_servers": [],
            "features": ["basic_chat"]
        }
    }


@pytest.fixture
def pro_config():
    """Create a Pro plan configuration."""
    return {
        "ai_provider": "openai",
        "openai_token": "test_token_12345678901234567890",
        "plan": "pro",
        "models": {"openai": "GLM-4.6"},
        "mcp_servers": ["zai-mcp-server", "web-search-prime"],
        "plan_capabilities": {
            "mcp_servers": ["zai-mcp-server", "web-search-prime"],
            "features": ["basic_chat", "image_analysis", "web_search"]
        }
    }


@pytest.fixture
def max_config():
    """Create a Max plan configuration."""
    return {
        "ai_provider": "openai",
        "openai_token": "test_token_12345678901234567890",
        "plan": "max",
        "models": {"openai": "GLM-4.6"},
        "mcp_servers": ["zai-mcp-server", "web-search-prime"],
        "plan_capabilities": {
            "mcp_servers": ["zai-mcp-server", "web-search-prime"],
            "features": ["basic_chat", "image_analysis", "web_search", "advanced_features"]
        }
    }


class TestMCPIntegrationManager:
    """Test MCP integration manager."""

    def test_lite_plan_mcp_unavailable(self, mock_hass, lite_config):
        """Test that MCP is unavailable for Lite plan."""
        mcp_manager = MCPIntegrationManager(mock_hass, lite_config)
        
        assert not mcp_manager.is_mcp_available()
        assert mcp_manager.get_available_mcp_tools() == []
        assert mcp_manager.get_mcp_status()["available"] is False

    def test_pro_plan_mcp_available(self, mock_hass, pro_config):
        """Test that MCP is available for Pro plan."""
        mcp_manager = MCPIntegrationManager(mock_hass, pro_config)
        
        assert mcp_manager.is_mcp_available()
        expected_tools = ["image_analysis", "video_analysis", "webSearchPrime"]
        assert set(mcp_manager.get_available_mcp_tools()) == set(expected_tools)
        assert mcp_manager.get_mcp_status()["available"] is True
        assert mcp_manager.get_mcp_status()["plan"] == "pro"

    def test_max_plan_mcp_available(self, mock_hass, max_config):
        """Test that MCP is available for Max plan."""
        mcp_manager = MCPIntegrationManager(mock_hass, max_config)
        
        assert mcp_manager.is_mcp_available()
        expected_tools = ["image_analysis", "video_analysis", "webSearchPrime"]
        assert set(mcp_manager.get_available_mcp_tools()) == set(expected_tools)
        assert mcp_manager.get_mcp_status()["available"] is True
        assert mcp_manager.get_mcp_status()["plan"] == "max"

    @pytest.mark.asyncio
    async def test_initialize_mcp_connections_pro(self, mock_hass, pro_config):
        """Test MCP connection initialization for Pro plan."""
        mcp_manager = MCPIntegrationManager(mock_hass, pro_config)
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_get.return_value.__aenter__.return_value = mock_response
            
            success = await mcp_manager.initialize_mcp_connections()
            
            assert success
            assert "web-search-prime" in mcp_manager.active_connections
            assert "zai-mcp-server" in mcp_manager.active_connections

    @pytest.mark.asyncio
    async def test_analyze_image_success(self, mock_hass, pro_config):
        """Test successful image analysis."""
        mcp_manager = MCPIntegrationManager(mock_hass, pro_config)
        
        mock_result = {"analysis": "This is a test image analysis result"}
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_result)
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await mcp_manager.call_mcp_tool("image_analysis", {
                "image_source": "https://example.com/image.jpg",
                "prompt": "Analyze this image"
            })
            
            assert result["success"] is True
            assert result["result"] == mock_result

    @pytest.mark.asyncio
    async def test_web_search_success(self, mock_hass, pro_config):
        """Test successful web search."""
        mcp_manager = MCPIntegrationManager(mock_hass, pro_config)
        
        mock_result = {
            "results": [
                {
                    "title": "Test Result",
                    "url": "https://example.com",
                    "summary": "Test summary"
                }
            ]
        }
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_result)
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await mcp_manager.call_mcp_tool("webSearchPrime", {
                "query": "test search query",
                "count": 5
            })
            
            assert result["success"] is True
            assert result["result"] == mock_result

    @pytest.mark.asyncio
    async def test_analyze_image_unavailable_lite(self, mock_hass, lite_config):
        """Test that image analysis is unavailable for Lite plan."""
        mcp_manager = MCPIntegrationManager(mock_hass, lite_config)
        
        result = await mcp_manager.call_mcp_tool("image_analysis", {
            "image_source": "https://example.com/image.jpg"
        })
        
        assert result["success"] is False
        assert "not available" in result["error"]

    @pytest.mark.asyncio
    async def test_disconnect_mcp_servers(self, mock_hass, pro_config):
        """Test disconnecting MCP servers."""
        mcp_manager = MCPIntegrationManager(mock_hass, pro_config)
        
        # Mock active connections
        mcp_manager.active_connections = {
            "web-search-prime": {
                "type": "http",
                "session": MagicMock()
            },
            "zai-mcp-server": {
                "type": "stdio",
                "config": {}
            }
        }
        
        await mcp_manager.disconnect_mcp_servers()
        
        assert len(mcp_manager.active_connections) == 0


class TestAgentMCPIntegration:
    """Test agent MCP integration."""

    @pytest.mark.asyncio
    async def test_agent_with_lite_plan_mcp_methods(self, mock_hass, lite_config):
        """Test agent MCP methods with Lite plan."""
        agent = AiAgentHaAgent(mock_hass, lite_config)
        
        # Test image analysis
        result = await agent.analyze_image("https://example.com/image.jpg")
        assert result["error"] is not None
        assert "Pro or Max plans" in result["error"]
        
        # Test video analysis
        result = await agent.analyze_video("https://example.com/video.mp4")
        assert result["error"] is not None
        assert "Pro or Max plans" in result["error"]
        
        # Test web search
        result = await agent.web_search("test query")
        assert result["error"] is not None
        assert "Pro or Max plans" in result["error"]
        
        # Test MCP status
        status = await agent.get_mcp_status()
        assert status["available"] is False
        assert status["plan"] == "lite"

    @pytest.mark.asyncio
    async def test_agent_with_pro_plan_mcp_methods(self, mock_hass, pro_config):
        """Test agent MCP methods with Pro plan."""
        agent = AiAgentHaAgent(mock_hass, pro_config)
        
        # Mock MCP manager
        agent.mcp_manager = MagicMock()
        agent.mcp_manager.is_mcp_available.return_value = True
        agent.mcp_manager.call_mcp_tool = AsyncMock(return_value={
            "success": True,
            "result": {"analysis": "test result"}
        })
        
        # Test image analysis
        result = await agent.analyze_image("https://example.com/image.jpg", "Test prompt")
        assert result["success"] is True
        agent.mcp_manager.call_mcp_tool.assert_called_with("image_analysis", {
            "image_source": "https://example.com/image.jpg",
            "prompt": "Test prompt"
        })
        
        # Test video analysis
        result = await agent.analyze_video("https://example.com/video.mp4", "Test prompt")
        assert result["success"] is True
        agent.mcp_manager.call_mcp_tool.assert_called_with("video_analysis", {
            "video_source": "https://example.com/video.mp4",
            "prompt": "Test prompt"
        })
        
        # Test web search
        result = await agent.web_search("test query", 10, "day")
        assert result["success"] is True
        agent.mcp_manager.call_mcp_tool.assert_called_with("webSearchPrime", {
            "query": "test query",
            "count": 10,
            "search_recency_filter": "day"
        })

    @pytest.mark.asyncio
    async def test_initialize_mcp_integration(self, mock_hass, pro_config):
        """Test MCP integration initialization."""
        agent = AiAgentHaAgent(mock_hass, pro_config)
        
        # Mock MCP manager
        agent.mcp_manager = MagicMock()
        agent.mcp_manager.is_mcp_available.return_value = True
        agent.mcp_manager.initialize_mcp_connections = AsyncMock(return_value=True)
        
        result = await agent.initialize_mcp_integration()
        
        assert result is True
        agent.mcp_manager.initialize_mcp_connections.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_query_with_mcp_tools(self, mock_hass, pro_config):
        """Test process_query with MCP tools."""
        agent = AiAgentHaAgent(mock_hass, pro_config)
        
        # Mock MCP manager
        agent.mcp_manager = MagicMock()
        agent.mcp_manager.is_mcp_available.return_value = True
        agent.mcp_manager.call_mcp_tool = AsyncMock(return_value={
            "success": True,
            "result": {"analysis": "test image analysis"}
        })
        
        # Mock AI client to return MCP tool request
        mock_response = json.dumps({
            "request_type": "data_request",
            "request": "analyze_image",
            "parameters": {
                "image_source": "https://example.com/image.jpg",
                "prompt": "Analyze this image"
            }
        })
        
        agent.ai_client.get_response = AsyncMock(return_value=mock_response)
        
        result = await agent.process_query("Analyze this image for me")
        
        assert result["success"] is True
        agent.mcp_manager.call_mcp_tool.assert_called_with("analyze_image", {
            "image_source": "https://example.com/image.jpg",
            "prompt": "Analyze this image"
        })

    @pytest.mark.asyncio
    async def test_process_query_with_web_search(self, mock_hass, pro_config):
        """Test process_query with web search."""
        agent = AiAgentHaAgent(mock_hass, pro_config)
        
        # Mock MCP manager
        agent.mcp_manager = MagicMock()
        agent.mcp_manager.is_mcp_available.return_value = True
        agent.mcp_manager.call_mcp_tool = AsyncMock(return_value={
            "success": True,
            "result": {
                "results": [
                    {
                        "title": "Test Result",
                        "url": "https://example.com",
                        "summary": "Test summary"
                    }
                ]
            }
        })
        
        # Mock AI client to return web search request
        mock_response = json.dumps({
            "request_type": "data_request",
            "request": "web_search",
            "parameters": {
                "query": "latest news about AI",
                "count": 5
            }
        })
        
        agent.ai_client.get_response = AsyncMock(return_value=mock_response)
        
        result = await agent.process_query("Search for latest news about AI")
        
        assert result["success"] is True
        agent.mcp_manager.call_mcp_tool.assert_called_with("webSearchPrime", {
            "query": "latest news about AI",
            "count": 5,
            "search_recency_filter": "noLimit"
        })