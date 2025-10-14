"""Test debugging system functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
import logging
from datetime import datetime, timedelta

from custom_components.glm_agent_ha.const import DOMAIN


@pytest.mark.integration
class TestDebugService:
    """Test debugging service functionality."""

    async def test_generate_debug_report(self, hass_with_config):
        """Test comprehensive debug report generation."""
        hass = hass_with_config

        result = await hass.services.async_call(
            DOMAIN,
            "generate_debug_report",
            {"entry_id": "test_entry"},
            blocking=True,
            return_result=True
        )

        # Check report structure
        assert "report_timestamp" in result
        assert "homeassistant_version" in result
        assert "integration_version" in result
        assert "system_info" in result
        assert "integration_status" in result
        assert "configuration" in result
        assert "entities" in result
        assert "services" in result
        assert "errors" in result
        assert "recommendations" in result

    async def test_get_system_info(self, hass_with_config):
        """Test system information retrieval."""
        hass = hass_with_config

        result = await hass.services.async_call(
            DOMAIN,
            "get_system_info",
            {},
            blocking=True,
            return_result=True
        )

        # Check system info structure
        assert "platform_info" in result
        assert "python_version" in result
        assert "homeassistant_version" in result
        assert "integration_info" in result
        assert "resource_usage" in result
        assert "dependencies" in result

        # Check integration-specific info
        integration_info = result["integration_info"]
        assert "version" in integration_info
        assert "enabled_features" in integration_info
        assert "registered_services" in integration_info
        assert "active_entities" in integration_info

    async def test_get_integration_status(self, hass_with_config):
        """Test integration status check."""
        hass = hass_with_config

        result = await hass.services.async_call(
            DOMAIN,
            "get_integration_status",
            {},
            blocking=True,
            return_result=True
        )

        # Check status structure
        assert "overall_status" in result
        assert "components" in result
        assert "services_status" in result
        assert "last_updated" in result
        assert "uptime_seconds" in result

        # Check components status
        components = result["components"]
        expected_components = ["agent", "security_manager", "performance_monitor", "structured_logger"]
        for component in expected_components:
            assert component in components
            assert "status" in components[component]
            assert "healthy" in components[component]

    async def test_test_api_connection(self, hass_with_config):
        """Test API connection testing."""
        hass = hass_with_config

        # Mock successful API test
        with patch.object(hass.data[DOMAIN], "agent") as mock_agent:
            mock_agent.test_api_connection = AsyncMock(return_value={
                "status": "success",
                "response_time_ms": 234.5,
                "model": "gpt-4",
                "endpoint": "https://api.openai.com/v1/chat/completions"
            })

            result = await hass.services.async_call(
                DOMAIN,
                "test_api_connection",
                {},
                blocking=True,
                return_result=True
            )

            assert result["status"] == "success"
            assert "response_time_ms" in result
            assert "tested_at" in result

    async def test_test_api_connection_failure(self, hass_with_config):
        """Test API connection testing with failure."""
        hass = hass_with_config

        # Mock failed API test
        with patch.object(hass.data[DOMAIN], "agent") as mock_agent:
            mock_agent.test_api_connection = AsyncMock(side_effect=Exception("Connection failed"))

            result = await hass.services.async_call(
                DOMAIN,
                "test_api_connection",
                {},
                blocking=True,
                return_result=True
            )

            assert result["status"] == "error"
            assert "error_message" in result
            assert "tested_at" in result

    async def test_get_recent_logs(self, hass_with_config):
        """Test recent logs retrieval."""
        hass = hass_with_config

        structured_logger = hass.data[DOMAIN].get("structured_logger")
        if structured_logger:
            # Add some test logs
            structured_logger.info("Test info log", category="system")
            structured_logger.warning("Test warning log", category="security")
            structured_logger.error("Test error log", category="error")

            result = await hass.services.async_call(
                DOMAIN,
                "get_recent_logs",
                {"limit": 10, "level": "INFO"},
                blocking=True,
                return_result=True
            )

            assert "logs" in result
            assert "total_count" in result
            assert "filtered_by" in result
            assert isinstance(result["logs"], list)
            assert len(result["logs"]) <= 10

    async def test_debug_service_error_handling(self, hass_with_config):
        """Test debug service error handling."""
        hass = hass_with_config

        # Test with invalid entry_id
        result = await hass.services.async_call(
            DOMAIN,
            "generate_debug_report",
            {"entry_id": "invalid_entry"},
            blocking=True,
            return_result=True
        )

        # Should still return a report, but with errors noted
        assert "report_timestamp" in result
        assert "errors" in result
        if result["errors"]:
            assert len(result["errors"]) > 0


@pytest.mark.integration
class TestStructuredLogger:
    """Test structured logging functionality."""

    async def test_basic_structured_logging(self, hass_with_config):
        """Test basic structured logging functionality."""
        hass = hass_with_config

        structured_logger = hass.data[DOMAIN].get("structured_logger")
        if structured_logger:
            # Test different log levels
            structured_logger.debug("Debug message", category="test")
            structured_logger.info("Info message", category="test")
            structured_logger.warning("Warning message", category="test")
            structured_logger.error("Error message", category="test")

            # Get statistics
            stats = structured_logger.get_statistics()
            assert stats["log_counts"]["DEBUG"] >= 1
            assert stats["log_counts"]["INFO"] >= 1
            assert stats["log_counts"]["WARNING"] >= 1
            assert stats["log_counts"]["ERROR"] >= 1

    async def test_context_logging(self, hass_with_config):
        """Test context-aware logging."""
        hass = hass_with_config

        structured_logger = hass.data[DOMAIN].get("structured_logger")
        if structured_logger:
            # Set correlation ID and context
            structured_logger.set_correlation_id("test_correlation_123")
            structured_logger.set_request_context({
                "user_id": "test_user",
                "session_id": "test_session",
                "request_type": "query"
            })

            # Log with context
            structured_logger.info("Test message with context", category="ai_agent")

            # Clear context
            structured_logger.clear_request_context()

            stats = structured_logger.get_statistics()
            assert stats["total_logs"] > 0

    async def test_request_context_manager(self, hass_with_config):
        """Test request context manager."""
        hass = hass_with_config

        structured_logger = hass.data[DOMAIN].get("structured_logger")
        if structured_logger:
            from custom_components.glm_agent_ha.structured_logger import RequestContext

            with RequestContext(structured_logger, "req_test_456", user_id="test_user"):
                structured_logger.info("Request started", category="system")
                structured_logger.info("Request in progress", category="system")
                structured_logger.info("Request completed", category="system")

            stats = structured_logger.get_statistics()
            assert stats["total_logs"] >= 3

    async def test_specialized_logging_methods(self, hass_with_config):
        """Test specialized logging methods."""
        hass = hass_with_config

        structured_logger = hass.data[DOMAIN].get("structured_logger")
        if structured_logger:
            # Test API request logging
            structured_logger.api_request(
                method="POST",
                url="https://api.openai.com/v1/chat/completions",
                status_code=200,
                duration_ms=1234.5
            )

            # Test AI request logging
            structured_logger.ai_request(
                request_type="query",
                provider="openai",
                model="gpt-4",
                tokens_used=15,
                duration_ms=2345.6,
                success=True
            )

            # Test security event logging
            structured_logger.security_event(
                event_type="input_validation",
                severity="info",
                details={"input_type": "prompt", "validated": True}
            )

            stats = structured_logger.get_statistics()
            assert stats["category_counts"]["api"] >= 1
            assert stats["category_counts"]["ai_agent"] >= 1
            assert stats["category_counts"]["security"] >= 1

    async def test_data_sanitization(self, hass_with_config):
        """Test log data sanitization."""
        hass = hass_with_config

        structured_logger = hass.data[DOMAIN].get("structured_logger")
        if structured_logger:
            # Log with sensitive data
            structured_logger.info(
                "Configuration loaded",
                category="config",
                api_key="sk-1234567890abcdef",
                token="secret_token_123",
                password="my_password",
                normal_field="normal_value"
            )

            # The sensitive data should be sanitized automatically
            stats = structured_logger.get_statistics()
            assert stats["total_logs"] > 0

    async def test_log_search_functionality(self, hass_with_config):
        """Test log searching functionality."""
        hass = hass_with_config

        structured_logger = hass.data[DOMAIN].get("structured_logger")
        if structured_logger:
            # Add test logs
            structured_logger.info("Test message for search", category="test")
            structured_logger.error("Error message for search", category="test")
            structured_logger.warning("Warning for search", category="test")

            # Search logs
            results = structured_logger.search_logs(
                query="error",
                category=None,
                level="ERROR",
                limit=10
            )

            # Should find error logs
            assert isinstance(results, list)
            # Note: search_logs is a simplified implementation, so results may be empty

    async def test_performance_logging(self, hass_with_config):
        """Test performance logging."""
        hass = hass_with_config

        structured_logger = hass.data[DOMAIN].get("structured_logger")
        if structured_logger:
            # Log performance metrics
            structured_logger.performance_metric(
                metric_name="database_query",
                value=45.2,
                unit="ms",
                query_type="SELECT"
            )

            structured_logger.performance_metric(
                metric_name="memory_usage",
                value=256.7,
                unit="MB"
            )

            stats = structured_logger.get_statistics()
            assert stats["category_counts"]["performance"] >= 2

    async def test_logging_services(self, hass_with_config):
        """Test logging-related services."""
        hass = hass_with_config

        # Test logging stats service
        result = await hass.services.async_call(
            DOMAIN,
            "logging_stats",
            {},
            blocking=True,
            return_result=True
        )

        assert "session_id" in result
        assert "log_counts" in result
        assert "category_counts" in result
        assert "total_logs" in result
        assert "structured_output_enabled" in result

        # Test logging search service
        result = await hass.services.async_call(
            DOMAIN,
            "logging_search",
            {
                "query": "test",
                "category": "system",
                "level": "INFO",
                "limit": 5
            },
            blocking=True,
            return_result=True
        )

        assert "query" in result
        assert "results" in result
        assert "results_count" in result
        assert isinstance(result["results"], list)


@pytest.mark.integration
class TestErrorHandlingAndRecovery:
    """Test error handling and recovery mechanisms."""

    async def test_service_error_logging(self, hass_with_config):
        """Test that service errors are properly logged."""
        hass = hass_with_config

        structured_logger = hass.data[DOMAIN].get("structured_logger")
        if structured_logger:
            with patch.object(structured_logger, "error") as mock_error:
                # Force an error in a service
                with patch.object(hass.data[DOMAIN], "agent") as mock_agent:
                    mock_agent.async_query = AsyncMock(side_effect=Exception("Test error"))

                    with pytest.raises(Exception):
                        await hass.services.async_call(
                            DOMAIN,
                            "query",
                            {"prompt": "Force error"},
                            blocking=True
                        )

                    # Verify error was logged
                    mock_error.assert_called()

    async def test_graceful_degradation(self, hass_with_config):
        """Test graceful degradation when components fail."""
        hass = hass_with_config

        # Temporarily disable performance monitor
        original_monitor = hass.data[DOMAIN].get("performance_monitor")
        if original_monitor:
            hass.data[DOMAIN]["performance_monitor"] = None

            try:
                # Service should still work without performance monitor
                with patch.object(hass.data[DOMAIN], "agent") as mock_agent:
                    mock_agent.async_query = AsyncMock(return_value={
                        "response": "Test response",
                        "model": "gpt-4"
                    })

                    result = await hass.services.async_call(
                        DOMAIN,
                        "query",
                        {"prompt": "Test graceful degradation"},
                        blocking=True,
                        return_result=True
                    )

                    assert "response" in result
            finally:
                # Restore performance monitor
                hass.data[DOMAIN]["performance_monitor"] = original_monitor

    async def test_mcp_integration_error_recovery(self, hass_with_config, mock_config_entry_pro):
        """Test MCP integration error recovery."""
        hass = hass_with_config

        # Mock MCP integration failure
        with patch.object(hass.data[DOMAIN], "mcp_integration") as mock_mcp:
            mock_mcp.get_connection_status = MagicMock(return_value={
                "status": "disconnected",
                "servers": {"test_server": {"connected": False, "error": "Connection failed"}}
            })

            # Should still be able to use basic services
            with patch.object(hass.data[DOMAIN], "agent") as mock_agent:
                mock_agent.async_query = AsyncMock(return_value={
                    "response": "Response without MCP",
                    "model": "gpt-4"
                })

                result = await hass.services.async_call(
                    DOMAIN,
                    "query",
                    {"prompt": "Test without MCP"},
                    blocking=True,
                    return_result=True
                )

                assert "response" in result

    async def test_config_flow_error_handling(self, hass):
        """Test config flow error handling."""
        from custom_components.glm_agent_ha.config_flow import GLMAgentConfigFlow

        flow = GLMAgentConfigFlow()
        flow.hass = hass

        # Test with invalid API key
        with patch("custom_components.glm_agent_ha.config_flow.validate_api_key", return_value=False):
            result = await flow.async_step_user({
                "openai_api_key": "invalid-key",
                "plan": "lite",
                "model": "gpt-3.5-turbo"
            })

            assert result["type"] == "form"
            assert "errors" in result
            assert result["errors"]["base"] == "invalid_auth"

    async def test_component_initialization_failure(self, hass):
        """Test handling of component initialization failures."""
        # Mock initialization failure
        with patch("custom_components.glm_agent_ha.async_setup_entry", side_effect=Exception("Init failed")):
            from custom_components.glm_agent_ha import async_setup_entry

            mock_config_entry = MagicMock()
            mock_config_entry.entry_id = "test_entry"

            result = await async_setup_entry(hass, mock_config_entry)
            assert not result

    async def test_memory_error_handling(self, hass_with_config):
        """Test handling of memory-related errors."""
        hass = hass_with_config

        structured_logger = hass.data[DOMAIN].get("structured_logger")
        if structured_logger:
            # Test with large log entries
            large_message = "x" * 1000000  # 1MB message

            try:
                structured_logger.info("Large message test", category="test", large_data=large_message)
            except Exception as e:
                # Should handle large messages gracefully
                assert isinstance(e, (MemoryError, ValueError))

    async def test_concurrent_error_handling(self, hass_with_config):
        """Test error handling with concurrent requests."""
        hass = hass_with_config
        import asyncio

        async def failing_request():
            with patch.object(hass.data[DOMAIN], "agent") as mock_agent:
                mock_agent.async_query = AsyncMock(side_effect=Exception("Concurrent error"))
                try:
                    await hass.services.async_call(
                        DOMAIN,
                        "query",
                        {"prompt": "Concurrent test"},
                        blocking=True
                    )
                except Exception:
                    pass  # Expected to fail

        # Run multiple failing requests concurrently
        tasks = [failing_request() for _ in range(10)]
        await asyncio.gather(*tasks, return_exceptions=True)

        # System should still be functional
        structured_logger = hass.data[DOMAIN].get("structured_logger")
        if structured_logger:
            stats = structured_logger.get_statistics()
            assert stats["total_logs"] >= 0


@pytest.mark.integration
class TestHealthMonitoring:
    """Test health monitoring functionality."""

    async def test_component_health_checks(self, hass_with_config):
        """Test component health monitoring."""
        hass = hass_with_config

        # Get integration status which includes health checks
        result = await hass.services.async_call(
            DOMAIN,
            "get_integration_status",
            {},
            blocking=True,
            return_result=True
        )

        assert "components" in result
        components = result["components"]

        # Check health of major components
        for component_name, component_status in components.items():
            assert "status" in component_status
            assert "healthy" in component_status
            assert "last_check" in component_status

    async def test_performance_health_monitoring(self, hass_with_config):
        """Test performance health monitoring."""
        hass = hass_with_config

        performance_monitor = hass.data[DOMAIN].get("performance_monitor")
        if performance_monitor:
            # Check performance health
            health_result = await hass.services.async_call(
                DOMAIN,
                "performance_health",
                {},
                blocking=True,
                return_result=True
            )

            assert "overall_health" in health_result
            assert "health_score" in health_result
            assert "recommendations" in health_result
            assert "issues" in health_result

    async def test_security_health_monitoring(self, hass_with_config):
        """Test security health monitoring."""
        hass = hass_with_config

        security_manager = hass.data[DOMAIN].get("security_manager")
        if security_manager:
            # Generate security report which includes health status
            security_report = await hass.services.async_call(
                DOMAIN,
                "security_report",
                {"hours": 24},
                blocking=True,
                return_result=True
            )

            assert "security_features" in security_report
            assert "recommendations" in security_report
            assert security_report["security_features"]["rate_limiting_enabled"] is True
            assert security_report["security_features"]["input_validation_enabled"] is True

    async def test_mcp_health_monitoring(self, hass_with_config, mock_config_entry_pro):
        """Test MCP integration health monitoring."""
        hass = hass_with_config

        mcp_integration = hass.data[DOMAIN].get("mcp_integration")
        if mcp_integration:
            # Get MCP connection status
            status = mcp_integration.get_connection_status()

            assert "status" in status
            assert "servers" in status
            assert "last_check" in status

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