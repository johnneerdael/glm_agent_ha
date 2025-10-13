"""MCP (Model Context Protocol) integration for GLM AI Agent HA."""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Union

import aiohttp
from homeassistant.core import HomeAssistant

from .const import (
    CONF_MCP_SERVERS,
    CONF_ENABLE_MCP_INTEGRATION,
)

_LOGGER = logging.getLogger(__name__)


class MCPIntegrationManager:
    """Manages MCP server integrations for GLM AI Agent HA."""

    def __init__(self, hass: HomeAssistant, config: Dict[str, Any]):
        """Initialize the MCP integration manager."""
        self.hass = hass
        self.config = config
        self.api_token = config.get("openai_token", "")
        self.plan = config.get("plan", "lite")
        self.mcp_servers = config.get("mcp_servers", [])
        self.plan_capabilities = config.get("plan_capabilities", {})
        self.enable_mcp = config.get(CONF_ENABLE_MCP_INTEGRATION, True)
        
        # MCP server configurations
        self.mcp_configs = {
            "zai-mcp-server": {
                "type": "stdio",
                "command": "npx",
                "args": ["-y", "@z_ai/mcp-server"],
                "env": {"Z_AI_API_KEY": self.api_token, "Z_AI_MODE": "ZAI"}
            },
            "web-search-prime": {
                "type": "streamable-http",
                "url": "https://api.z.ai/api/mcp/web_search_prime/mcp",
                "headers": {"Authorization": f"Bearer {self.api_token}"}
            }
        }
        
        # Active MCP connections
        self.active_connections: Dict[str, Any] = {}

    def is_mcp_available(self) -> bool:
        """Check if MCP integration is available for the current plan."""
        return (
            self.enable_mcp and
            self.plan in ["pro", "max"] and
            bool(self.mcp_servers) and
            bool(self.api_token)
        )

    def get_available_mcp_tools(self) -> List[str]:
        """Get list of available MCP tools based on the current plan."""
        if not self.is_mcp_available():
            return []
        
        tools = []
        for server in self.mcp_servers:
            if server == "zai-mcp-server":
                tools.extend(["image_analysis", "video_analysis"])
            elif server == "web-search-prime":
                tools.append("webSearchPrime")
        
        return tools

    async def initialize_mcp_connections(self) -> bool:
        """Initialize MCP server connections for Pro/Max plans."""
        if not self.is_mcp_available():
            _LOGGER.debug("MCP integration not available for plan: %s", self.plan)
            return False

        _LOGGER.info("Initializing MCP connections for plan: %s", self.plan)
        
        success = True
        for server_name in self.mcp_servers:
            if server_name in self.mcp_configs:
                try:
                    if await self._connect_mcp_server(server_name):
                        _LOGGER.info("Successfully connected to MCP server: %s", server_name)
                    else:
                        _LOGGER.warning("Failed to connect to MCP server: %s", server_name)
                        success = False
                except Exception as e:
                    _LOGGER.error("Error connecting to MCP server %s: %s", server_name, e)
                    success = False
        
        return success

    async def _connect_mcp_server(self, server_name: str) -> bool:
        """Connect to a specific MCP server."""
        if server_name not in self.mcp_configs:
            _LOGGER.error("Unknown MCP server: %s", server_name)
            return False

        config = self.mcp_configs[server_name]
        
        try:
            if config["type"] == "stdio":
                # Handle stdio MCP server (zai-mcp-server)
                return await self._connect_stdio_server(server_name, config)
            elif config["type"] == "streamable-http":
                # Handle HTTP MCP server (web-search-prime)
                return await self._connect_http_server(server_name, config)
            else:
                _LOGGER.error("Unsupported MCP server type: %s", config["type"])
                return False
        except Exception as e:
            _LOGGER.error("Error connecting to MCP server %s: %s", server_name, e)
            return False

    async def _connect_stdio_server(self, server_name: str, config: Dict[str, Any]) -> bool:
        """Connect to stdio-based MCP server."""
        # For stdio servers, we'll use a subprocess-based approach
        # This is a simplified implementation - in production, you'd want proper process management
        try:
            # Store connection info for later use
            self.active_connections[server_name] = {
                "type": "stdio",
                "config": config,
                "status": "connected"
            }
            _LOGGER.debug("Initialized stdio MCP server: %s", server_name)
            return True
        except Exception as e:
            _LOGGER.error("Failed to initialize stdio MCP server %s: %s", server_name, e)
            return False

    async def _connect_http_server(self, server_name: str, config: Dict[str, Any]) -> bool:
        """Connect to HTTP-based MCP server."""
        try:
            # Test connection with a simple request
            async with aiohttp.ClientSession() as session:
                headers = config.get("headers", {})
                async with session.get(
                    config["url"],
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        self.active_connections[server_name] = {
                            "type": "http",
                            "config": config,
                            "session": session,
                            "status": "connected"
                        }
                        _LOGGER.debug("Successfully connected to HTTP MCP server: %s", server_name)
                        return True
                    else:
                        _LOGGER.error("HTTP MCP server returned status %d: %s", response.status, server_name)
                        return False
        except Exception as e:
            _LOGGER.error("Failed to connect to HTTP MCP server %s: %s", server_name, e)
            return False

    async def call_mcp_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool by name."""
        if not self.is_mcp_available():
            return {
                "success": False,
                "error": f"MCP integration not available for plan: {self.plan}"
            }

        # Determine which server handles this tool
        server_name = self._get_server_for_tool(tool_name)
        if not server_name:
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}"
            }

        if server_name not in self.active_connections:
            return {
                "success": False,
                "error": f"MCP server not connected: {server_name}"
            }

        try:
            if tool_name in ["image_analysis", "video_analysis"]:
                return await self._call_zai_mcp_tool(tool_name, parameters)
            elif tool_name == "webSearchPrime":
                return await self._call_web_search_tool(parameters)
            else:
                return {
                    "success": False,
                    "error": f"Unsupported tool: {tool_name}"
                }
        except Exception as e:
            _LOGGER.error("Error calling MCP tool %s: %s", tool_name, e)
            return {
                "success": False,
                "error": f"Error calling tool {tool_name}: {str(e)}"
            }

    def _get_server_for_tool(self, tool_name: str) -> Optional[str]:
        """Get the MCP server name that handles a specific tool."""
        if tool_name in ["image_analysis", "video_analysis"]:
            return "zai-mcp-server"
        elif tool_name == "webSearchPrime":
            return "web-search-prime"
        return None

    async def _call_zai_mcp_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Call Z.AI MCP server tools (image/video analysis)."""
        try:
            # For stdio-based MCP servers, we'd normally use subprocess communication
            # This is a simplified implementation that directly calls the API
            if tool_name == "image_analysis":
                return await self._analyze_image(parameters)
            elif tool_name == "video_analysis":
                return await self._analyze_video(parameters)
            else:
                return {
                    "success": False,
                    "error": f"Unknown Z.AI tool: {tool_name}"
                }
        except Exception as e:
            _LOGGER.error("Error calling Z.AI MCP tool %s: %s", tool_name, e)
            return {
                "success": False,
                "error": f"Error calling Z.AI tool {tool_name}: {str(e)}"
            }

    async def _analyze_image(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze an image using Z.AI API."""
        try:
            image_source = parameters.get("image_source")
            prompt = parameters.get("prompt", "Analyze this image")
            
            if not image_source:
                return {
                    "success": False,
                    "error": "image_source parameter is required"
                }

            # Call Z.AI image analysis API
            url = "https://api.z.ai/api/v1/analyze_image"
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "image_source": image_source,
                "prompt": prompt
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        return {
                            "success": True,
                            "result": result
                        }
                    else:
                        error_text = await response.text()
                        _LOGGER.error("Z.AI image analysis API error %d: %s", response.status, error_text)
                        return {
                            "success": False,
                            "error": f"API error {response.status}: {error_text}"
                        }
        except Exception as e:
            _LOGGER.error("Error in image analysis: %s", e)
            return {
                "success": False,
                "error": f"Image analysis error: {str(e)}"
            }

    async def _analyze_video(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a video using Z.AI API."""
        try:
            video_source = parameters.get("video_source")
            prompt = parameters.get("prompt", "Analyze this video")
            
            if not video_source:
                return {
                    "success": False,
                    "error": "video_source parameter is required"
                }

            # Call Z.AI video analysis API
            url = "https://api.z.ai/api/v1/analyze_video"
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "video_source": video_source,
                "prompt": prompt
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        return {
                            "success": True,
                            "result": result
                        }
                    else:
                        error_text = await response.text()
                        _LOGGER.error("Z.AI video analysis API error %d: %s", response.status, error_text)
                        return {
                            "success": False,
                            "error": f"API error {response.status}: {error_text}"
                        }
        except Exception as e:
            _LOGGER.error("Error in video analysis: %s", e)
            return {
                "success": False,
                "error": f"Video analysis error: {str(e)}"
            }

    async def _call_web_search_tool(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Call web search tool."""
        try:
            search_query = parameters.get("query")
            if not search_query:
                return {
                    "success": False,
                    "error": "query parameter is required"
                }

            # Call Z.AI web search API
            url = "https://api.z.ai/api/mcp/web_search_prime/search"
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "search_query": search_query,
                "count": parameters.get("count", 5),
                "search_recency_filter": parameters.get("search_recency_filter", "noLimit")
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        return {
                            "success": True,
                            "result": result
                        }
                    else:
                        error_text = await response.text()
                        _LOGGER.error("Z.AI web search API error %d: %s", response.status, error_text)
                        return {
                            "success": False,
                            "error": f"API error {response.status}: {error_text}"
                        }
        except Exception as e:
            _LOGGER.error("Error in web search: %s", e)
            return {
                "success": False,
                "error": f"Web search error: {str(e)}"
            }

    async def disconnect_mcp_servers(self):
        """Disconnect all MCP servers."""
        _LOGGER.info("Disconnecting MCP servers")
        
        for server_name, connection in self.active_connections.items():
            try:
                if connection.get("type") == "http" and "session" in connection:
                    await connection["session"].close()
                _LOGGER.debug("Disconnected MCP server: %s", server_name)
            except Exception as e:
                _LOGGER.error("Error disconnecting MCP server %s: %s", server_name, e)
        
        self.active_connections.clear()

    def get_mcp_status(self) -> Dict[str, Any]:
        """Get the status of MCP integration."""
        return {
            "available": self.is_mcp_available(),
            "plan": self.plan,
            "enabled_servers": self.mcp_servers,
            "active_connections": list(self.active_connections.keys()),
            "available_tools": self.get_available_mcp_tools()
        }