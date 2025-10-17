"""MCP (Model Context Protocol) integration for GLM AI Agent HA."""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional, Union

import aiohttp
from homeassistant.core import HomeAssistant

# Try to import FastMCP for native Python MCP support
try:
    from fastmcp import Client as FastMCPClient
    FASTMCP_AVAILABLE = True
except ImportError:
    FASTMCP_AVAILABLE = False
    FastMCPClient = None

from .const import (
    CONF_MCP_SERVERS,
    CONF_ENABLE_MCP_INTEGRATION,
)

_LOGGER = logging.getLogger(__name__)

# MCP monitoring and retry constants
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY_BASE = 1.0  # Base delay in seconds
MAX_RETRY_DELAY = 30.0  # Maximum delay in seconds
HEALTH_CHECK_INTERVAL = 300  # Health check every 5 minutes
CONNECTION_TIMEOUT = 30  # Connection timeout in seconds
REQUEST_TIMEOUT = 60  # Request timeout in seconds


class NativeMCPServer:
    """Base class for native Python MCP servers."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the native MCP server."""
        self.config = config
        self.is_connected = False

    async def connect(self) -> bool:
        """Connect to the MCP server."""
        try:
            # Native Python MCP servers connect directly
            self.is_connected = True
            return True
        except Exception as e:
            _LOGGER.error("Failed to connect to native MCP server: %s", e)
            return False

    async def disconnect(self):
        """Disconnect from the MCP server."""
        self.is_connected = False

    async def call_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the MCP server."""
        raise NotImplementedError("Subclasses must implement call_tool")


class ZAIMCPServer(NativeMCPServer):
    """Native Python implementation of Z.AI MCP server."""

    async def call_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Call a Z.AI MCP tool."""
        try:
            api_key = self.config.get("api_key")
            if not api_key:
                return {
                    "success": False,
                    "error": "API key not configured"
                }

            if tool_name == "image_analysis":
                return await self._analyze_image(parameters, api_key)
            elif tool_name == "video_analysis":
                return await self._analyze_video(parameters, api_key)
            else:
                return {
                    "success": False,
                    "error": f"Unknown tool: {tool_name}"
                }
        except Exception as e:
            _LOGGER.error("Error in Z.AI MCP server: %s", e)
            return {
                "success": False,
                "error": f"Z.AI server error: {str(e)}"
            }

    async def _analyze_image(self, parameters: Dict[str, Any], api_key: str) -> Dict[str, Any]:
        """Analyze an image using Z.AI API."""
        try:
            image_source = parameters.get("image_source")
            prompt = parameters.get("prompt", "Analyze this image")

            if not image_source:
                return {
                    "success": False,
                    "error": "image_source parameter is required"
                }

            url = "https://api.z.ai/api/v1/analyze_image"
            headers = {
                "Authorization": f"Bearer {api_key}",
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
                        return {"success": True, "result": result}
                    else:
                        error_text = await response.text()
                        _LOGGER.error("Z.AI image analysis API error %d: %s", response.status, error_text)
                        return {
                            "success": False,
                            "error": f"API error {response.status}: {error_text}"
                        }
        except Exception as e:
            _LOGGER.error("Error in native image analysis: %s", e)
            return {
                "success": False,
                "error": f"Image analysis error: {str(e)}"
            }

    async def _analyze_video(self, parameters: Dict[str, Any], api_key: str) -> Dict[str, Any]:
        """Analyze a video using Z.AI API."""
        try:
            video_source = parameters.get("video_source")
            prompt = parameters.get("prompt", "Analyze this video")

            if not video_source:
                return {
                    "success": False,
                    "error": "video_source parameter is required"
                }

            url = "https://api.z.ai/api/v1/analyze_video"
            headers = {
                "Authorization": f"Bearer {api_key}",
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
                        return {"success": True, "result": result}
                    else:
                        error_text = await response.text()
                        _LOGGER.error("Z.AI video analysis API error %d: %s", response.status, error_text)
                        return {
                            "success": False,
                            "error": f"API error {response.status}: {error_text}"
                        }
        except Exception as e:
            _LOGGER.error("Error in native video analysis: %s", e)
            return {
                "success": False,
                "error": f"Video analysis error: {str(e)}"
            }


class WebSearchMCPServer(NativeMCPServer):
    """Native Python implementation of Web Search MCP server."""

    async def call_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Call a web search tool."""
        try:
            api_key = self.config.get("api_key")
            if not api_key:
                return {
                    "success": False,
                    "error": "API key not configured"
                }

            if tool_name == "webSearchPrime":
                return await self._web_search(parameters, api_key)
            else:
                return {
                    "success": False,
                    "error": f"Unknown tool: {tool_name}"
                }
        except Exception as e:
            _LOGGER.error("Error in Web Search MCP server: %s", e)
            return {
                "success": False,
                "error": f"Web search server error: {str(e)}"
            }

    async def _web_search(self, parameters: Dict[str, Any], api_key: str) -> Dict[str, Any]:
        """Perform web search using Z.AI API."""
        try:
            search_query = parameters.get("query")
            if not search_query:
                return {
                    "success": False,
                    "error": "query parameter is required"
                }

            url = "https://api.z.ai/api/mcp/web_search_prime/search"
            headers = {
                "Authorization": f"Bearer {api_key}",
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
                        return {"success": True, "result": result}
                    else:
                        error_text = await response.text()
                        _LOGGER.error("Z.AI web search API error %d: %s", response.status, error_text)
                        return {
                            "success": False,
                            "error": f"API error {response.status}: {error_text}"
                        }
        except Exception as e:
            _LOGGER.error("Error in native web search: %s", e)
            return {
                "success": False,
                "error": f"Web search error: {str(e)}"
            }


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

        # MCP server configurations with native Python FastMCP support
        self.mcp_configs = {
            "zai-mcp-server": {
                "type": "native-python",
                "server_class": "ZAIMCPServer",
                "config": {
                    "api_key": self.api_token,
                    "mode": "ZAI"
                },
                "fallback": {
                    "type": "stdio",
                    "command": "npx",
                    "args": ["-y", "@z_ai/mcp-server"],
                    "env": {"Z_AI_API_KEY": self.api_token, "Z_AI_MODE": "ZAI"}
                }
            },
            "web-search-prime": {
                "type": "native-python",
                "server_class": "WebSearchMCPServer",
                "config": {
                    "api_key": self.api_token,
                    "base_url": "https://api.z.ai/api/mcp/web_search_prime/mcp"
                },
                "fallback": {
                    "type": "streamable-http",
                    "url": "https://api.z.ai/api/mcp/web_search_prime/mcp",
                    "headers": {"Authorization": f"Bearer {self.api_token}"}
                }
            }
        }

        # Active MCP connections with enhanced monitoring
        self.active_connections: Dict[str, Any] = {}

        # Monitoring and health check data
        self.connection_stats: Dict[str, Dict[str, Any]] = {}
        self.health_check_task: Optional[asyncio.Task] = None
        self._shutdown = False

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
        """Initialize MCP server connections for Pro/Max plans with monitoring."""
        if not self.is_mcp_available():
            _LOGGER.debug("MCP integration not available for plan: %s", self.plan)
            return False

        _LOGGER.info("Initializing MCP connections for plan: %s", self.plan)

        # Initialize connection statistics
        for server_name in self.mcp_servers:
            if server_name not in self.connection_stats:
                self.connection_stats[server_name] = {
                    "connected_at": None,
                    "last_success": None,
                    "last_failure": None,
                    "failure_count": 0,
                    "total_requests": 0,
                    "successful_requests": 0,
                    "avg_response_time": 0.0,
                    "status": "disconnected"
                }

        success = True
        for server_name in self.mcp_servers:
            if server_name in self.mcp_configs:
                try:
                    if await self._connect_mcp_server_with_retry(server_name):
                        _LOGGER.info("Successfully connected to MCP server: %s", server_name)
                        self.connection_stats[server_name]["status"] = "connected"
                        self.connection_stats[server_name]["connected_at"] = time.time()
                        self.connection_stats[server_name]["last_success"] = time.time()
                    else:
                        _LOGGER.warning("Failed to connect to MCP server: %s", server_name)
                        self.connection_stats[server_name]["status"] = "failed"
                        self.connection_stats[server_name]["last_failure"] = time.time()
                        self.connection_stats[server_name]["failure_count"] += 1
                        success = False
                except Exception as e:
                    _LOGGER.error("Error connecting to MCP server %s: %s", server_name, e)
                    self.connection_stats[server_name]["status"] = "error"
                    self.connection_stats[server_name]["last_failure"] = time.time()
                    self.connection_stats[server_name]["failure_count"] += 1
                    success = False

        # Start health monitoring if connections were established
        if success and not self.health_check_task and not self._shutdown:
            self.health_check_task = self.hass.async_create_task(
                self._health_check_loop()
            )
            _LOGGER.info("Started MCP health monitoring")

        return success

    async def _connect_mcp_server_with_retry(self, server_name: str) -> bool:
        """Connect to MCP server with retry logic."""
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                result = await self._connect_mcp_server(server_name)
                if result:
                    if attempt > 0:
                        _LOGGER.info("MCP server %s connected after %d attempts", server_name, attempt + 1)
                    return True
            except Exception as e:
                _LOGGER.warning("MCP server %s connection attempt %d failed: %s", server_name, attempt + 1, e)

                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    # Exponential backoff with jitter
                    delay = min(RETRY_DELAY_BASE * (2 ** attempt) + (hash(server_name) % 1), MAX_RETRY_DELAY)
                    await asyncio.sleep(delay)

        _LOGGER.error("MCP server %s failed to connect after %d attempts", server_name, MAX_RETRY_ATTEMPTS)
        return False

    async def _health_check_loop(self):
        """Background health check loop for MCP connections."""
        while not self._shutdown and self.is_mcp_available():
            try:
                await asyncio.sleep(HEALTH_CHECK_INTERVAL)

                if self._shutdown:
                    break

                await self._perform_health_checks()

            except asyncio.CancelledError:
                _LOGGER.debug("Health check loop cancelled")
                break
            except Exception as e:
                _LOGGER.error("Error in health check loop: %s", e)
                await asyncio.sleep(60)  # Wait 1 minute before retrying

    async def _perform_health_checks(self):
        """Perform health checks on all MCP connections."""
        for server_name in list(self.active_connections.keys()):
            try:
                stats = self.connection_stats.get(server_name, {})

                if server_name == "web-search-prime":
                    # Test HTTP server with a simple health check
                    healthy = await self._health_check_http_server(server_name)
                else:
                    # For stdio servers, check if process is still responsive
                    healthy = await self._health_check_stdio_server(server_name)

                if healthy:
                    stats["last_success"] = time.time()
                    stats["status"] = "healthy"
                    _LOGGER.debug("Health check passed for MCP server: %s", server_name)
                else:
                    stats["last_failure"] = time.time()
                    stats["failure_count"] += 1
                    stats["status"] = "unhealthy"
                    _LOGGER.warning("Health check failed for MCP server: %s", server_name)

                    # Attempt to reconnect if unhealthy
                    if stats["failure_count"] >= 3:
                        _LOGGER.info("Attempting to reconnect unhealthy MCP server: %s", server_name)
                        await self._reconnect_server(server_name)

            except Exception as e:
                _LOGGER.error("Health check error for server %s: %s", server_name, e)
                if server_name in self.connection_stats:
                    self.connection_stats[server_name]["last_failure"] = time.time()
                    self.connection_stats[server_name]["status"] = "error"

    async def _health_check_http_server(self, server_name: str) -> bool:
        """Health check for HTTP-based MCP servers."""
        try:
            config = self.mcp_configs.get(server_name)
            if not config or config.get("type") != "streamable-http":
                return False

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                headers = config.get("headers", {})
                async with session.get(
                    config["url"],
                    headers=headers
                ) as response:
                    return response.status == 200
        except Exception:
            return False

    async def _health_check_stdio_server(self, server_name: str) -> bool:
        """Health check for stdio-based MCP servers."""
        # For stdio servers, we'd normally check if the process is still alive
        # This is a simplified implementation
        connection = self.active_connections.get(server_name)
        return connection is not None and connection.get("status") == "connected"

    async def _reconnect_server(self, server_name: str):
        """Attempt to reconnect a failed MCP server."""
        try:
            # Remove old connection
            if server_name in self.active_connections:
                del self.active_connections[server_name]

            # Attempt to reconnect
            if await self._connect_mcp_server_with_retry(server_name):
                _LOGGER.info("Successfully reconnected MCP server: %s", server_name)
                self.connection_stats[server_name]["status"] = "connected"
                self.connection_stats[server_name]["connected_at"] = time.time()
                self.connection_stats[server_name]["last_success"] = time.time()
                self.connection_stats[server_name]["failure_count"] = 0
            else:
                _LOGGER.error("Failed to reconnect MCP server: %s", server_name)
                self.connection_stats[server_name]["status"] = "failed"

        except Exception as e:
            _LOGGER.error("Error reconnecting MCP server %s: %s", server_name, e)

    async def _connect_mcp_server(self, server_name: str) -> bool:
        """Connect to a specific MCP server with native Python preference and fallback support."""
        if server_name not in self.mcp_configs:
            _LOGGER.error("Unknown MCP server: %s", server_name)
            return False

        config = self.mcp_configs[server_name]

        try:
            # Try native Python implementation first
            if config["type"] == "native-python":
                return await self._connect_native_server(server_name, config)
            elif config["type"] == "stdio":
                # Handle stdio MCP server (fallback)
                return await self._connect_stdio_server(server_name, config)
            elif config["type"] == "streamable-http":
                # Handle HTTP MCP server (fallback)
                return await self._connect_http_server(server_name, config)
            else:
                _LOGGER.error("Unsupported MCP server type: %s", config["type"])
                return False
        except Exception as e:
            _LOGGER.error("Error connecting to MCP server %s: %s", server_name, e)
            return False

    async def _connect_native_server(self, server_name: str, config: Dict[str, Any]) -> bool:
        """Connect to a native Python MCP server."""
        try:
            server_class_name = config.get("server_class")
            server_config = config.get("config", {})

            # Create the appropriate server instance
            if server_class_name == "ZAIMCPServer":
                server = ZAIMCPServer(server_config)
            elif server_class_name == "WebSearchMCPServer":
                server = WebSearchMCPServer(server_config)
            else:
                _LOGGER.error("Unknown native MCP server class: %s", server_class_name)
                return False

            # Try to connect
            if await server.connect():
                self.active_connections[server_name] = {
                    "type": "native-python",
                    "server": server,
                    "config": config,
                    "status": "connected"
                }
                _LOGGER.info("Successfully connected to native Python MCP server: %s", server_name)
                return True
            else:
                _LOGGER.warning("Failed to connect to native Python MCP server: %s", server_name)
                return False

        except Exception as e:
            _LOGGER.error("Error connecting to native Python MCP server %s: %s", server_name, e)

            # Try fallback if available
            fallback_config = config.get("fallback")
            if fallback_config:
                _LOGGER.info("Attempting fallback connection for MCP server: %s", server_name)
                return await self._connect_fallback_server(server_name, fallback_config)

            return False

    async def _connect_fallback_server(self, server_name: str, fallback_config: Dict[str, Any]) -> bool:
        """Connect to a fallback MCP server configuration."""
        try:
            fallback_type = fallback_config.get("type")

            if fallback_type == "stdio":
                return await self._connect_stdio_server(server_name, fallback_config)
            elif fallback_type == "streamable-http":
                return await self._connect_http_server(server_name, fallback_config)
            else:
                _LOGGER.error("Unsupported fallback MCP server type: %s", fallback_type)
                return False

        except Exception as e:
            _LOGGER.error("Error connecting to fallback MCP server %s: %s", server_name, e)
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
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                headers = config.get("headers", {})
                try:
                    async with session.get(
                        config["url"],
                        headers=headers
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
                            _LOGGER.warning("HTTP MCP server returned status %d: %s - MCP features will be unavailable", response.status, server_name)
                            return False
                except aiohttp.ClientError as e:
                    _LOGGER.warning("HTTP MCP server connection failed for %s: %s - MCP features will be unavailable", server_name, e)
                    return False
        except Exception as e:
            _LOGGER.warning("Failed to connect to HTTP MCP server %s: %s - MCP features will be unavailable", server_name, e)
            return False

    async def call_mcp_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool by name with monitoring and retry logic."""
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

        # Update request statistics
        if server_name in self.connection_stats:
            self.connection_stats[server_name]["total_requests"] += 1

        start_time = time.time()

        try:
            result = await self._call_mcp_tool_with_retry(tool_name, parameters, server_name)

            # Update success statistics
            end_time = time.time()
            response_time = end_time - start_time

            if server_name in self.connection_stats:
                stats = self.connection_stats[server_name]
                if result.get("success"):
                    stats["successful_requests"] += 1
                    stats["last_success"] = time.time()
                    stats["status"] = "healthy"

                # Update average response time
                total_requests = stats["total_requests"]
                current_avg = stats["avg_response_time"]
                stats["avg_response_time"] = ((current_avg * (total_requests - 1)) + response_time) / total_requests

            _LOGGER.debug("MCP tool %s completed in %.2fs", tool_name, response_time)
            return result

        except Exception as e:
            # Update failure statistics
            end_time = time.time()
            response_time = end_time - start_time

            if server_name in self.connection_stats:
                stats = self.connection_stats[server_name]
                stats["last_failure"] = time.time()
                stats["failure_count"] += 1
                stats["status"] = "error"

            _LOGGER.error("Error calling MCP tool %s after %.2fs: %s", tool_name, response_time, e)
            return {
                "success": False,
                "error": f"Error calling tool {tool_name}: {str(e)}",
                "response_time": response_time
            }

    async def _call_mcp_tool_with_retry(self, tool_name: str, parameters: Dict[str, Any], server_name: str) -> Dict[str, Any]:
        """Call MCP tool with retry logic using native Python servers when available."""
        last_error = None

        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                # Get the connection for this server
                connection = self.active_connections.get(server_name)
                if not connection:
                    return {
                        "success": False,
                        "error": f"MCP server not connected: {server_name}"
                    }

                # Use native Python server if available
                if connection.get("type") == "native-python":
                    server = connection.get("server")
                    if server:
                        return await server.call_tool(tool_name, parameters)

                # Fallback to direct API calls
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
                last_error = e
                _LOGGER.warning("MCP tool %s attempt %d failed: %s", tool_name, attempt + 1, e)

                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    # Check if we need to reconnect the server
                    if "connection" in str(e).lower() or "timeout" in str(e).lower():
                        _LOGGER.info("Connection issue detected, attempting to reconnect server: %s", server_name)
                        await self._reconnect_server(server_name)

                    # Exponential backoff with jitter
                    jitter = hash(server_name) % 1000 / 1000  # 0-1 second jitter
                    delay = min(RETRY_DELAY_BASE * (2 ** attempt) + jitter, MAX_RETRY_DELAY)
                    await asyncio.sleep(delay)

        # All attempts failed
        return {
            "success": False,
            "error": f"Tool {tool_name} failed after {MAX_RETRY_ATTEMPTS} attempts: {str(last_error)}"
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
        """Disconnect all MCP servers and cleanup monitoring."""
        _LOGGER.info("Disconnecting MCP servers and stopping monitoring")

        # Stop health monitoring
        self._shutdown = True
        if self.health_check_task and not self.health_check_task.done():
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass

        # Disconnect all active connections
        for server_name, connection in self.active_connections.items():
            try:
                connection_type = connection.get("type")

                if connection_type == "native-python":
                    # Disconnect native Python servers
                    server = connection.get("server")
                    if server and hasattr(server, "disconnect"):
                        await server.disconnect()
                elif connection_type == "http" and "session" in connection:
                    # Close HTTP sessions
                    await connection["session"].close()

                _LOGGER.debug("Disconnected MCP server: %s (type: %s)", server_name, connection_type)
            except Exception as e:
                _LOGGER.error("Error disconnecting MCP server %s: %s", server_name, e)

        self.active_connections.clear()
        self.connection_stats.clear()

    def get_mcp_status(self) -> Dict[str, Any]:
        """Get comprehensive status of MCP integration."""
        total_requests = sum(stats.get("total_requests", 0) for stats in self.connection_stats.values())
        successful_requests = sum(stats.get("successful_requests", 0) for stats in self.connection_stats.values())
        success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0

        return {
            "available": self.is_mcp_available(),
            "plan": self.plan,
            "enabled_servers": self.mcp_servers,
            "active_connections": list(self.active_connections.keys()),
            "available_tools": self.get_available_mcp_tools(),
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "success_rate": round(success_rate, 2),
            "health_monitoring_active": self.health_check_task is not None and not self._shutdown,
            "server_stats": self.connection_stats
        }

    async def analyze_image(self, image_url: str, prompt: str = "Describe this image in detail for AI analysis") -> str:
        """Analyze an image using MCP - simplified interface for AI Task entity."""
        try:
            result = await self.call_mcp_tool("image_analysis", {
                "image_source": image_url,
                "prompt": prompt
            })

            if result.get("success"):
                analysis = result.get("result", {})
                if isinstance(analysis, dict) and "description" in analysis:
                    return analysis["description"]
                elif isinstance(analysis, str):
                    return analysis
                else:
                    return str(analysis)
            else:
                raise Exception(f"Image analysis failed: {result.get('error', 'Unknown error')}")

        except Exception as e:
            _LOGGER.error("Failed to analyze image: %s", e)
            raise

    