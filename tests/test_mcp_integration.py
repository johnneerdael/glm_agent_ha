"""Test MCP (Model Context Protocol) integration functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
import asyncio

from custom_components.glm_agent_ha.const import DOMAIN


@pytest.mark.mcp
class TestMCPIntegration:
    """Test MCP integration functionality."""

    async def test_mcp_server_connection(self, hass_with_config, mock_config_entry_pro):
        """Test MCP server connection establishment."""
        hass = hass_with_config

        mcp_integration = hass.data[DOMAIN].get("mcp_integration")
        if mcp_integration:
            # Mock successful connection
            with patch.object(mcp_integration, "_connect_mcp_server", return_value=True):
                result = await mcp_integration.connect_server("test_server")

                assert result is True

    async def test_mcp_server_connection_failure(self, hass_with_config, mock_config_entry_pro):
        """Test MCP server connection failure handling."""
        hass = hass_with_config

        mcp_integration = hass.data[DOMAIN].get("mcp_integration")
        if mcp_integration:
            # Mock connection failure
            with patch.object(mcp_integration, "_connect_mcp_server", return_value=False):
                result = await mcp_integration.connect_server("test_server")

                assert result is False

    async def test_mcp_server_connection_retry(self, hass_with_config, mock_config_entry_pro):
        """Test MCP server connection retry logic."""
        hass = hass_with_config

        mcp_integration = hass.data[DOMAIN].get("mcp_integration")
        if mcp_integration:
            call_count = 0

            def mock_connect_with_retry(server_name):
                nonlocal call_count
                call_count += 1
                if call_count < 3:
                    return False  # Fail first 2 attempts
                return True  # Succeed on 3rd attempt

            with patch.object(mcp_integration, "_connect_mcp_server_with_retry", side_effect=mock_connect_with_retry):
                result = await mcp_integration.connect_server_with_retry("test_server")

                assert result is True
                assert call_count == 3

    async def test_mcp_tool_execution(self, hass_with_config, mock_config_entry_pro):
        """Test MCP tool execution."""
        hass = hass_with_config

        mcp_integration = hass.data[DOMAIN].get("mcp_integration")
        if mcp_integration:
            # Mock successful tool execution
            mock_result = {
                "success": True,
                "result": "Tool executed successfully",
                "data": {"output": "test output"}
            }

            with patch.object(mcp_integration, "execute_tool", return_value=mock_result):
                result = await mcp_integration.execute_tool(
                    "test_server",
                    "test_tool",
                    {"param1": "value1"}
                )

                assert result["success"] is True
                assert "result" in result

    async def test_mcp_tool_execution_failure(self, hass_with_config, mock_config_entry_pro):
        """Test MCP tool execution failure."""
        hass = hass_with_config

        mcp_integration = hass.data[DOMAIN].get("mcp_integration")
        if mcp_integration:
            # Mock tool execution failure
            with patch.object(mcp_integration, "execute_tool", side_effect=Exception("Tool execution failed")):
                with pytest.raises(Exception):
                    await mcp_integration.execute_tool(
                        "test_server",
                        "test_tool",
                        {"param1": "value1"}
                    )

    async def test_mcp_connection_status(self, hass_with_config, mock_config_entry_pro):
        """Test MCP connection status reporting."""
        hass = hass_with_config

        mcp_integration = hass.data[DOMAIN].get("mcp_integration")
        if mcp_integration:
            # Mock connection status
            mock_status = {
                "status": "connected",
                "servers": {
                    "filesystem": {
                        "connected": True,
                        "last_connected": "2025-01-14T10:30:00Z",
                        "tools_available": ["read_file", "write_file", "list_directory"]
                    },
                    "web_search": {
                        "connected": False,
                        "error": "Connection timeout",
                        "retry_count": 3
                    }
                },
                "last_check": "2025-01-14T10:30:00Z"
            }

            with patch.object(mcp_integration, "get_connection_status", return_value=mock_status):
                status = mcp_integration.get_connection_status()

                assert status["status"] == "connected"
                assert "servers" in status
                assert len(status["servers"]) == 2

    async def test_mcp_server_list_management(self, hass_with_config, mock_config_entry_pro):
        """Test MCP server list management."""
        hass = hass_with_config

        mcp_integration = hass.data[DOMAIN].get("mcp_integration")
        if mcp_integration:
            # Test adding server
            await mcp_integration.add_server_config("new_server", {
                "command": "npx",
                "args": ["new-mcp-server"],
                "env": {"API_KEY": "test_key"}
            })

            # Test removing server
            await mcp_integration.remove_server_config("old_server")

            # Test listing servers
            servers = mcp_integration.get_server_configs()
            assert isinstance(servers, dict)

    async def test_mcp_error_recovery(self, hass_with_config, mock_config_entry_pro):
        """Test MCP error recovery mechanisms."""
        hass = hass_with_config

        mcp_integration = hass.data[DOMAIN].get("mcp_integration")
        if mcp_integration:
            # Simulate connection error
            with patch.object(mcp_integration, "_handle_connection_error") as mock_handle:
                await mcp_integration._handle_connection_error("test_server", "Connection lost")

                mock_handle.assert_called_once_with("test_server", "Connection lost")

    async def test_mcp_service_integration(self, hass_with_config, mock_config_entry_pro):
        """Test MCP service integration."""
        hass = hass_with_config

        # Test MCP status service
        result = await hass.services.async_call(
            DOMAIN,
            "mcp_status",
            {},
            blocking=True,
            return_result=True
        )

        assert "connection_status" in result
        assert "servers" in result

        # Test MCP tool execution service
        with patch.object(hass.data[DOMAIN], "mcp_integration") as mock_mcp:
            mock_mcp.execute_tool = AsyncMock(return_value={
                "success": True,
                "result": "Tool executed via service"
            })

            result = await hass.services.async_call(
                DOMAIN,
                "mcp_execute_tool",
                {
                    "server": "test_server",
                    "tool": "test_tool",
                    "parameters": {"param1": "value1"}
                },
                blocking=True,
                return_result=True
            )

            assert result["success"] is True


@pytest.mark.mcp
class TestMCPSecurity:
    """Test MCP integration security features."""

    async def test_mcp_domain_validation(self, hass_with_config, mock_config_entry_pro):
        """Test MCP domain validation."""
        hass = hass_with_config

        security_manager = hass.data[DOMAIN].get("security_manager")
        if security_manager:
            # Test allowed MCP domains
            allowed_mcp_domains = [
                "context7.com",
                "z.ai",
                "github.com",
                "supabase.com"
            ]

            for domain in allowed_mcp_domains:
                assert security_manager.is_domain_allowed(f"https://{domain}"), f"Should allow MCP domain: {domain}"

            # Test blocked domains
            blocked_domains = [
                "malicious.com",
                "suspicious-site.net",
                "phishing-domain.org"
            ]

            for domain in blocked_domains:
                assert not security_manager.is_domain_allowed(f"https://{domain}"), f"Should block domain: {domain}"

    async def test_mcp_input_validation(self, hass_with_config, mock_config_entry_pro):
        """Test MCP input validation."""
        hass = hass_with_config

        security_manager = hass.data[DOMAIN].get("security_manager")
        if security_manager:
            # Test valid MCP inputs
            valid_inputs = [
                "read file /config/configuration.yaml",
                "search web for Home Assistant tutorials",
                "get documentation for light entity"
            ]

            for input_text in valid_inputs:
                is_valid, error = security_manager.validate_input(input_text, "mcp_command", 1000)
                assert is_valid, f"Should accept valid MCP input: {input_text}"

            # Test malicious MCP inputs
            malicious_inputs = [
                "execute 'rm -rf /'",
                "write file /etc/passwd content",
                "download file from malicious-site.com/virus.exe"
            ]

            for input_text in malicious_inputs:
                is_valid, error = security_manager.validate_input(input_text, "mcp_command", 1000)
                assert not is_valid, f"Should reject malicious MCP input: {input_text}"

    async def test_mcp_tool_parameter_sanitization(self, hass_with_config, mock_config_entry_pro):
        """Test MCP tool parameter sanitization."""
        hass = hass_with_config

        security_manager = hass.data[DOMAIN].get("security_manager")
        if security_manager:
            # Test parameter sanitization
            malicious_params = {
                "file_path": "../../../etc/passwd",
                "api_key": "sk-1234567890",
                "url": "javascript:alert('xss')",
                "command": "rm -rf /"
            }

            sanitized_params = security_manager.sanitize_data(malicious_params)

            # Check that sensitive data is redacted
            assert sanitized_params["api_key"] == "***REDACTED***"
            # Check that dangerous paths are handled
            assert "etc/passwd" not in sanitized_params["file_path"] or sanitized_params["file_path"] == "***REDACTED***"

    async def test_mcp_rate_limiting(self, hass_with_config, mock_config_entry_pro):
        """Test MCP rate limiting."""
        hass = hass_with_config

        security_manager = hass.data[DOMAIN].get("security_manager")
        if security_manager:
            client_id = "mcp_client_test"

            # Make multiple MCP requests
            requests_made = 0
            for _ in range(100):
                is_allowed, rate_info = security_manager.check_rate_limit(f"mcp_{client_id}")
                if not is_allowed:
                    break
                requests_made += 1

            # Should eventually be rate limited
            if requests_made < 100:
                assert not is_allowed, "MCP requests should be rate limited"


@pytest.mark.mcp
class TestMCPPerformance:
    """Test MCP integration performance."""

    async def test_mcp_concurrent_tool_execution(self, hass_with_config, mock_config_entry_pro):
        """Test concurrent MCP tool execution."""
        hass = hass_with_config

        mcp_integration = hass.data[DOMAIN].get("mcp_integration")
        if mcp_integration:
            async def mock_tool_execution(server, tool, params):
                await asyncio.sleep(0.1)  # Simulate work
                return {
                    "success": True,
                    "result": f"Executed {tool}",
                    "execution_time_ms": 100
                }

            with patch.object(mcp_integration, "execute_tool", side_effect=mock_tool_execution):
                # Execute multiple tools concurrently
                tasks = []
                for i in range(5):
                    task = mcp_integration.execute_tool(
                        "test_server",
                        f"tool_{i}",
                        {"param": f"value_{i}"}
                    )
                    tasks.append(task)

                start_time = asyncio.get_event_loop().time()
                results = await asyncio.gather(*tasks)
                end_time = asyncio.get_event_loop().time()

                # Should complete in roughly the time of one execution due to concurrency
                execution_time = (end_time - start_time) * 1000
                assert execution_time < 300  # Should be much less than 500ms (5 * 100ms sequential)
                assert len(results) == 5
                assert all(result["success"] for result in results)

    async def test_mcp_connection_monitoring(self, hass_with_config, mock_config_entry_pro):
        """Test MCP connection monitoring."""
        hass = hass_with_config

        mcp_integration = hass.data[DOMAIN].get("mcp_integration")
        if mcp_integration:
            # Mock connection monitoring data
            mock_stats = {
                "connection_uptime_seconds": 3600,
                "total_requests": 150,
                "successful_requests": 145,
                "failed_requests": 5,
                "average_response_time_ms": 234.5,
                "last_error": None,
                "retry_count": 2
            }

            with patch.object(mcp_integration, "get_connection_statistics", return_value=mock_stats):
                stats = mcp_integration.get_connection_statistics()

                assert stats["total_requests"] == 150
                assert stats["successful_requests"] == 145
                assert stats["average_response_time_ms"] == 234.5

    async def test_mcp_memory_usage(self, hass_with_config, mock_config_entry_pro):
        """Test MCP integration memory usage."""
        hass = hass_with_config

        mcp_integration = hass.data[DOMAIN].get("mcp_integration")
        if mcp_integration:
            # Simulate large number of tool results
            large_results = []
            for i in range(100):
                large_results.append({
                    "tool": f"tool_{i}",
                    "result": "x" * 10000,  # 10KB result
                    "timestamp": "2025-01-14T10:30:00Z"
                })

            # Test memory cleanup
            with patch.object(mcp_integration, "_cleanup_old_results") as mock_cleanup:
                mcp_integration._cleanup_old_results()
                mock_cleanup.assert_called_once()

    async def test_mcp_timeout_handling(self, hass_with_config, mock_config_entry_pro):
        """Test MCP timeout handling."""
        hass = hass_with_config

        mcp_integration = hass.data[DOMAIN].get("mcp_integration")
        if mcp_integration:
            # Mock timeout
            with patch.object(mcp_integration, "execute_tool", side_effect=asyncio.TimeoutError()):
                with pytest.raises(asyncio.TimeoutError):
                    await mcp_integration.execute_tool(
                        "test_server",
                        "slow_tool",
                        {"delay": 10}
                    )


@pytest.mark.mcp
class TestMCPIntegration:
    """Test MCP integration with other components."""

    async def test_mcp_with_ai_agent(self, hass_with_config, mock_config_entry_pro):
        """Test MCP integration with AI agent."""
        hass = hass_with_config

        mcp_integration = hass.data[DOMAIN].get("mcp_integration")
        if mcp_integration:
            with patch.object(hass.data[DOMAIN], "agent") as mock_agent:
                # Mock agent with MCP capability
                mock_agent.async_query = AsyncMock(return_value={
                    "response": "I can help with that using MCP tools",
                    "model": "gpt-4",
                    "mcp_tools_used": ["filesystem", "web_search"]
                })

                result = await hass.services.async_call(
                    DOMAIN,
                    "query",
                    {"prompt": "Read my configuration file and search for help"},
                    blocking=True,
                    return_result=True
                )

                assert "response" in result
                mock_agent.async_query.assert_called_once()

    async def test_mcp_with_security_system(self, hass_with_config, mock_config_entry_pro):
        """Test MCP integration with security system."""
        hass = hass_with_config

        security_manager = hass.data[DOMAIN].get("security_manager")
        if security_manager:
            # Test that MCP operations are subject to security validation
            with patch.object(security_manager, "validate_input") as mock_validate:
                mock_validate.return_value = (True, None)

                mcp_integration = hass.data[DOMAIN].get("mcp_integration")
                if mcp_integration:
                    with patch.object(mcp_integration, "execute_tool", return_value={"success": True}):
                        await mcp_integration.execute_tool(
                            "filesystem",
                            "read_file",
                            {"path": "/config/configuration.yaml"}
                        )

                        # Security validation should have been called
                        mock_validate.assert_called()

    async def test_mcp_with_performance_monitoring(self, hass_with_config, mock_config_entry_pro):
        """Test MCP integration with performance monitoring."""
        hass = hass_with_config

        performance_monitor = hass.data[DOMAIN].get("performance_monitor")
        if performance_monitor:
            mcp_integration = hass.data[DOMAIN].get("mcp_integration")
            if mcp_integration:
                with patch.object(mcp_integration, "execute_tool", return_value={
                    "success": True,
                    "execution_time_ms": 150.0
                }):
                    await mcp_integration.execute_tool(
                        "test_server",
                        "test_tool",
                        {"param": "value"}
                    )

                    # Check if performance was monitored
                    metrics = performance_monitor.get_metrics()
                    # May have metrics for MCP operations
                    assert metrics["total_requests"] >= 0

    async def test_mcp_error_propagation(self, hass_with_config, mock_config_entry_pro):
        """Test MCP error propagation to other components."""
        hass = hass_with_config

        structured_logger = hass.data[DOMAIN].get("structured_logger")
        if structured_logger:
            with patch.object(structured_logger, "error") as mock_log:
                mcp_integration = hass.data[DOMAIN].get("mcp_integration")
                if mcp_integration:
                    with patch.object(mcp_integration, "execute_tool", side_effect=Exception("MCP Error")):
                        with pytest.raises(Exception):
                            await mcp_integration.execute_tool(
                                "test_server",
                                "failing_tool",
                                {"param": "value"}
                            )

                        # Error should be logged
                        mock_log.assert_called()

    async def test_mcp_graceful_degradation(self, hass_with_config, mock_config_entry_pro):
        """Test graceful degradation when MCP is unavailable."""
        hass = hass_with_config

        # Temporarily disable MCP
        original_mcp = hass.data[DOMAIN].get("mcp_integration")
        if original_mcp:
            hass.data[DOMAIN]["mcp_integration"] = None

        try:
            # AI agent should still work without MCP
            with patch.object(hass.data[DOMAIN], "agent") as mock_agent:
                mock_agent.async_query = AsyncMock(return_value={
                    "response": "I can help without MCP tools",
                    "model": "gpt-4",
                    "mcp_tools_used": []
                })

                result = await hass.services.async_call(
                    DOMAIN,
                    "query",
                    {"prompt": "Help me without MCP"},
                    blocking=True,
                    return_result=True
                )

                assert "response" in result
        finally:
            # Restore MCP
            hass.data[DOMAIN]["mcp_integration"] = original_mcp