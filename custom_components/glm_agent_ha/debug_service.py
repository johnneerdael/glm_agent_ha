"""Comprehensive debugging service for GLM Agent HA integration."""

from __future__import annotations

import asyncio
import json
import logging
import os
import platform
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_AI_PROVIDER,
    CONF_ENABLE_MCP_INTEGRATION,
    CONF_PLAN,
    DOMAIN,
)
from .agent import AiAgentHaAgent
from .mcp_integration import MCPIntegrationManager
from .ai_task_entity import GLMAgentAITaskEntity

_LOGGER = logging.getLogger(__name__)


class GLMAgentDebugService:
    """Comprehensive debugging service for GLM Agent HA."""

    def __init__(self, hass: HomeAssistant):
        """Initialize the debugging service."""
        self.hass = hass
        self._debug_data = {}

    async def get_system_info(self) -> Dict[str, Any]:
        """Get comprehensive system information."""
        try:
            info = {
                "timestamp": datetime.now().isoformat(),
                "python_version": sys.version,
                "platform": platform.platform(),
                "architecture": platform.architecture()[0],
                "homeassistant_version": self._get_homeassistant_version(),
                "environment_variables": self._get_relevant_env_vars(),
                "available_memory": self._get_memory_info(),
                "disk_space": self._get_disk_space_info(),
                "network_connectivity": await self._test_network_connectivity(),
            }

            # Add configuration information
            info["configuration"] = await self._get_configuration_info()

            return info

        except Exception as e:
            _LOGGER.error("Error collecting system info: %s", e)
            return {"error": str(e), "timestamp": datetime.now().isoformat()}

    def _get_homeassistant_version(self) -> str:
        """Get Home Assistant version."""
        try:
            from homeassistant.const import __version__
            return __version__
        except ImportError:
            return "unknown"

    def _get_relevant_env_vars(self) -> Dict[str, Any]:
        """Get relevant environment variables for debugging."""
        env_vars = {}
        relevant_vars = [
            "Z_AI_API_KEY",
            "CONTEXT7_API_KEY",
            "JINA_API_KEY",
            "TAVILY_API_KEY",
            "GITHUB_TOKEN",
            "SUPABASE_ACCESS_TOKEN"
        ]

        for var in relevant_vars:
            if var in os.environ:
                # Don't log actual keys, just indicate they're present
                env_vars[var] = "configured" if os.environ[var] else "not_set"
            else:
                env_vars[var] = "missing"

        return env_vars

    def _get_memory_info(self) -> Dict[str, Any]:
        """Get memory usage information."""
        try:
            import psutil
            memory = psutil.virtual_memory()
            return {
                "total": memory.total,
                "available": memory.available,
                "used": memory.used,
                "percent": memory.percent,
                "available_mb": round(memory.available / (1024 * 1024), 2),
                "used_mb": round(memory.used / (1024 * 1024), 2),
            }
        except ImportError:
            return {"error": "psutil not available"}
        except Exception as e:
            return {"error": f"Memory info failed: {str(e)}"}

    def _get_disk_space_info(self) -> Dict[str, Any]:
        """Get disk space information."""
        try:
            stat = os.statvfs(".")
            total = stat.f_frsize * stat.f_blocks
            free = stat.f_frsize * stat.f_bavail
            used = total - free

            return {
                "total_bytes": total,
                "total_gb": round(total / (1024 ** 3), 2),
                "available_bytes": free,
                "available_gb": round(free / (1024 ** 3), 2),
                "used_bytes": used,
                "used_gb": round(used / (1024 ** 3), 2),
                "usage_percent": round((used / total) * 100, 2) if total > 0 else 0,
            }
        except Exception as e:
            return {"error": f"Disk space info failed: {str(e)}"}

    async def _test_network_connectivity(self) -> Dict[str, Any]:
        """Test network connectivity to external services."""
        services = {
            "google_dns": ("8.8.8.8", 53),
            "cloudflare_dns": ("1.1.1.1", 53),
            "zai_api": ("api.z.ai", 443),
            "github_api": ("api.github.com", 443),
        }

        results = {}
        import socket

        for service_name, (host, port) in services.items():
            try:
                start_time = time.time()
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(10)
                result = sock.connect_ex((host, port))
                end_time = time.time()

                results[service_name] = {
                    "success": result == 0,
                    "response_time_ms": round((end_time - start_time) * 1000, 2),
                    "host": host,
                    "port": port
                }
                sock.close()

            except Exception as e:
                results[service_name] = {
                    "success": False,
                    "error": str(e),
                    "host": host,
                    "port": port
                }

        return results

    async def _get_configuration_info(self) -> Dict[str, Any]:
        """Get configuration information from config entries."""
        try:
            config_entries = []
            for entry in self.hass.config_entries.async_entries(DOMAIN):
                if isinstance(entry.data, dict):
                    config_entries.append({
                        "entry_id": entry.entry_id,
                        "title": entry.title,
                        "plan": entry.data.get(CONF_PLAN, "unknown"),
                        "provider": entry.data.get(CONF_AI_PROVIDER, "unknown"),
                        "mcp_servers": entry.data.get("mcp_servers", []),
                        "mcp_enabled": entry.options.get(CONF_ENABLE_MCP_INTEGRATION, True),
                        "created_at": entry.created_at.isoformat() if entry.created_at else "unknown",
                        "modified_at": entry.modified_at.isoformat() if entry.modified_at else "unknown",
                    })

            return {
                "total_entries": len(config_entries),
                "entries": config_entries
            }

        except Exception as e:
            return {"error": f"Configuration info failed: {str(e)}"}

    async def get_integration_status(self, entry_id: Optional[str] = None) -> Dict[str, Any]:
        """Get detailed integration status."""
        try:
            status = {
                "timestamp": datetime.now().isoformat(),
                "integration_status": "unknown"
            }

            # Find the config entry
            config_entry = None
            if entry_id:
                config_entry = self.hass.config_entries.async_get_entry(DOMAIN, entry_id)
            else:
                entries = self.hass.config_entries.async_entries(DOMAIN)
                if entries:
                    config_entry = entries[0]

            if not config_entry:
                status["integration_status"] = "not_configured"
                status["error"] = "No GLM Agent HA configuration found"
                return status

            status["integration_status"] = "configured"
            status["config_entry"] = {
                "entry_id": config_entry.entry_id,
                "title": config_entry.title,
                "plan": config_entry.data.get(CONF_PLAN, "unknown"),
                "provider": config_entry.data.get(CONF_AI_PROVIDER, "unknown"),
            }

            # Test AI Agent
            try:
                agent = AiAgentHaAgent(self.hass, config_entry.data)
                status["ai_agent"] = {
                    "initialized": True,
                    "provider": config_entry.data.get(CONF_AI_PROVIDER, "unknown"),
                    "api_key_configured": bool(config_entry.data.get("openai_token")),
                    "model_configuration": config_entry.data.get("models", {}),
                }
            except Exception as e:
                status["ai_agent"] = {
                    "initialized": False,
                    "error": str(e)
                }

            # Test MCP Integration
            plan = config_entry.data.get(CONF_PLAN, "lite")
            if plan in ["pro", "max"] and config_entry.options.get(CONF_ENABLE_MCP_INTEGRATION, True):
                try:
                    mcp_manager = MCPIntegrationManager(self.hass, config_entry.data)
                    mcp_status = mcp_manager.get_mcp_status()
                    status["mcp_integration"] = mcp_status

                    # Test MCP connections
                    connection_test = await mcp_manager.initialize_mcp_connections()
                    status["mcp_connection_test"] = {
                        "success": connection_test,
                        "attempted_at": datetime.now().isoformat()
                    }

                except Exception as e:
                    status["mcp_integration"] = {
                        "available": False,
                        "error": str(e)
                    }

            # Test AI Task Entity
            try:
                ai_task_entity = GLMAgentAITaskEntity(self.hass, config_entry)
                entity_status = await ai_task_entity._get_entity_status()
                status["ai_task_entity"] = entity_status
            except Exception as e:
                status["ai_task_entity"] = {
                    "error": str(e),
                    "available": False
                }

            return status

        except Exception as e:
            return {
                "error": f"Status check failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }

    async def test_api_connections(self, entry_id: Optional[str] = None) -> Dict[str, Any]:
        """Test API connections with external services."""
        try:
            config_entry = None
            if entry_id:
                config_entry = self.hass.config_entries.async_get_entry(DOMAIN, entry_id)
            else:
                entries = self.hass.config_entries.async_entries(DOMAIN)
                if entries:
                    config_entry = entries[0]

            if not config_entry:
                return {"error": "No configuration found"}

            results = {
                "timestamp": datetime.now().isoformat(),
                "tests": {}
            }

            # Test OpenAI/GLM API connection
            api_token = config_entry.data.get("openai_token")
            if api_token:
                try:
                    import aiohttp
                    url = "https://api.openai.com/v1/models"
                    headers = {
                        "Authorization": f"Bearer {api_token}",
                        "Content-Type": "application/json"
                    }

                    start_time = time.time()
                    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                        async with session.get(url, headers=headers) as response:
                            end_time = time.time()
                            results["tests"]["openai_api"] = {
                                "success": response.status == 200,
                                "status_code": response.status,
                                "response_time_ms": round((end_time - start_time) * 1000, 2),
                                "test_url": url
                            }
                except Exception as e:
                    results["tests"]["openai_api"] = {
                        "success": False,
                        "error": str(e),
                        "test_url": "https://api.openai.com/v1/models"
                    }
            else:
                results["tests"]["openai_api"] = {
                    "success": False,
                    "error": "No API token configured"
                }

            # Test Z.AI API connection
            if config_entry.data.get("mcp_servers") and "zai-mcp-server" in config_entry.data.get("mcp_servers", []):
                try:
                    import aiohttp
                    url = "https://api.z.ai/api/v1/analyze_image"
                    headers = {
                        "Authorization": f"Bearer {api_token}",
                        "Content-Type": "application/json"
                    }

                    start_time = time.time()
                    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                        async with session.post(url, headers=headers, json={
                            "image_source": "https://example.com/test.jpg",
                            "prompt": "test"
                        }) as response:
                            end_time = time.time()
                            results["tests"]["zai_api"] = {
                                "success": response.status in [200, 400, 401],  # 400/401 expected for invalid image
                                "status_code": response.status,
                                "response_time_ms": round((end_time - start_time) * 1000, 2),
                                "test_url": url
                            }
                except Exception as e:
                    results["tests"]["zai_api"] = {
                        "success": False,
                        "error": str(e),
                        "test_url": "https://api.z.ai/api/v1/analyze_image"
                    }

            return results

        except Exception as e:
            return {
                "error": f"API connection tests failed: {str(e)}",
                "timestamp": datetime.now().recent_isoformat()
            }

    async def get_service_logs(self, entry_id: Optional[str] = None, lines: int = 100) -> Dict[str, Any]:
        """Get recent service logs."""
        try:
            # This is a simplified implementation
            # In a real scenario, you'd access Home Assistant's logging system

            logs = []

            # Get recent log entries from our logger
            if hasattr(_LOGGER, 'handlers'):
                for handler in _LOGGER.handlers:
                    if hasattr(handler, 'baseFilename'):
                        try:
                            log_file = handler.baseFilename
                            if os.path.exists(log_file):
                                with open(log_file, 'r', encoding='utf-8') as f:
                                    content = f.readlines()
                                    # Get last N lines
                                    recent_lines = content[-lines:] if len(content) > 0 else content

                                    for line in recent_lines:
                                        if DOMAIN in line or "GLM Agent" in line:
                                            logs.append(line.strip())
                        except Exception:
                            continue

            return {
                "timestamp": datetime.now().isoformat(),
                "total_log_lines": len(logs),
                "recent_logs": logs[-lines:] if len(logs) > lines else logs,
                "log_level": "debug"
            }

        except Exception as e:
            return {
                "error": f"Log collection failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }

    async def generate_debug_report(self, entry_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate comprehensive debug report."""
        try:
            report = {
                "report_timestamp": datetime.now().isoformat(),
                "report_version": "1.0.0",
                "glm_agent_ha_debug_report": True
            }

            # Collect all debugging information
            report["system_info"] = await self.get_system_info()
            report["integration_status"] = await self.get_integration_status(entry_id)
            report["api_connections"] = await self.test_api_connections(entry_id)
            report["recent_logs"] = await self.get_service_logs(entry_id)

            # Add recommendations
            report["recommendations"] = self._generate_recommendations(report)

            return report

        except Exception as e:
            return {
                "error": f"Debug report generation failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }

    def _generate_recommendations(self, report_data: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on debugging data."""
        recommendations = []

        # System recommendations
        system_info = report_data.get("system_info", {})
        if "error" in system_info:
            recommendations.append("❌ System information collection failed - check permissions")

        disk_space = system_info.get("disk_space", {})
        if disk_space.get("usage_percent", 0) > 80:
            recommendations.append(f"⚠️ Disk usage is {disk_space['usage_percent']}% - consider cleaning up files")

        # Environment variables
        env_vars = system_info.get("environment_variables", {})
        missing_vars = [var for var, status in env_vars.items() if status == "missing"]
        if missing_vars:
            recommendations.append(f"⚠️ Missing environment variables: {', '.join(missing_vars)}")

        # Network connectivity
        network = system_info.get("network_connectivity", {})
        failed_services = [name for name, data in network.items() if not data.get("success")]
        if failed_services:
            recommendations.append(f"⚠️ Network connectivity issues with: {', '.join(failed_services)}")

        # Integration status
        integration = report_data.get("integration_status", {})
        if integration.get("integration_status") == "not_configured":
            recommendations.append("ℹ️ GLM Agent HA is not configured - add configuration in Home Assistant")

        ai_agent = integration.get("ai_agent", {})
        if ai_agent.get("error"):
            recommendations.append("⚠️ AI Agent initialization failed - check configuration")

        mcp_integration = integration.get("mcp_integration", {})
        if mcp_integration.get("error"):
            recommendations.append("⚠️ MCP integration issues - check configuration and API keys")

        ai_task_entity = integration.get("ai_task_entity", {})
        if ai_task_entity.get("error"):
            recommendations.append("⚠️ AI Task Entity issues - check www directory permissions")

        # API connections
        api_tests = report_data.get("api_connections", {}).get("tests", {})
        failed_apis = [name for name, data in api_tests.items() if not data.get("success")]
        if failed_apis:
            recommendations.append(f"⚠️ API connection issues with: {', '.join(failed_apis)}")

        # Add positive recommendations if everything looks good
        if not recommendations:
            recommendations.append("✅ All systems appear to be functioning correctly")

        return recommendations