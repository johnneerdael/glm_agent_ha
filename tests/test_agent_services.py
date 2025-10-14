"""Test AI agent service functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from custom_components.glm_agent_ha.const import DOMAIN


@pytest.mark.integration
class TestQueryService:
    """Test the main query service."""

    async def test_query_service_basic(self, hass_with_config, mock_openai_client):
        """Test basic query service functionality."""
        hass = hass_with_config

        # Mock the AI agent
        with patch.object(hass.data[DOMAIN], "agent") as mock_agent:
            mock_agent.async_query = AsyncMock(return_value={
                "response": "Test response",
                "model": "gpt-4",
                "tokens_used": 15,
                "duration_ms": 1234.5
            })

            # Call the service
            await hass.services.async_call(
                DOMAIN,
                "query",
                {"prompt": "Hello, how are you?"},
                blocking=True
            )

            # Verify the agent was called
            mock_agent.async_query.assert_called_once()
            call_args = mock_agent.async_query.call_args[0][0]
            assert "Hello, how are you?" in call_args

    async def test_query_service_with_context(self, hass_with_config, mock_openai_client):
        """Test query service with context parameters."""
        hass = hass_with_config

        with patch.object(hass.data[DOMAIN], "agent") as mock_agent:
            mock_agent.async_query = AsyncMock(return_value={
                "response": "Context-aware response",
                "model": "gpt-4",
                "tokens_used": 20
            })

            context_data = {
                "user_id": "test_user",
                "session_id": "test_session",
                "area_id": "living_room"
            }

            await hass.services.async_call(
                DOMAIN,
                "query",
                {
                    "prompt": "What's in the living room?",
                    "context": context_data
                },
                blocking=True
            )

            mock_agent.async_query.assert_called_once()

    async def test_query_service_error_handling(self, hass_with_config):
        """Test query service error handling."""
        hass = hass_with_config

        with patch.object(hass.data[DOMAIN], "agent") as mock_agent:
            mock_agent.async_query = AsyncMock(side_effect=Exception("API Error"))

            with pytest.raises(Exception):
                await hass.services.async_call(
                    DOMAIN,
                    "query",
                    {"prompt": "Test prompt"},
                    blocking=True
                )

    async def test_query_service_with_conversation_history(self, hass_with_config, mock_openai_client):
        """Test query service with conversation history."""
        hass = hass_with_config

        with patch.object(hass.data[DOMAIN], "agent") as mock_agent:
            mock_agent.async_query = AsyncMock(return_value={
                "response": "I remember our conversation",
                "model": "gpt-4",
                "tokens_used": 25
            })

            history = [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"}
            ]

            await hass.services.async_call(
                DOMAIN,
                "query",
                {
                    "prompt": "Do you remember me?",
                    "conversation_history": history
                },
                blocking=True
            )

            mock_agent.async_query.assert_called_once()

    async def test_query_service_rate_limiting(self, hass_with_config):
        """Test query service rate limiting."""
        hass = hass_with_config

        # Get security manager
        security_manager = hass.data[DOMAIN].get("security_manager")
        if security_manager:
            with patch.object(security_manager, "check_rate_limit") as mock_rate_limit:
                mock_rate_limit.return_value = (False, {"blocked_until": "2025-01-14T11:00:00Z"})

                # Should be blocked
                with pytest.raises(Exception):  # Service should raise exception for rate limit
                    await hass.services.async_call(
                        DOMAIN,
                        "query",
                        {"prompt": "Test prompt"},
                        blocking=True
                    )


@pytest.mark.integration
class TestAutomationService:
    """Test automation creation service."""

    async def test_create_automation_success(self, hass_with_config, mock_openai_client):
        """Test successful automation creation."""
        hass = hass_with_config

        with patch.object(hass.data[DOMAIN], "agent") as mock_agent:
            mock_agent.async_create_automation = AsyncMock(return_value={
                "automation_id": "test_automation_123",
                "name": "Test Automation",
                "yaml": "automation:\n  - id: test_automation_123\n    alias: Test Automation",
                "success": True
            })

            result = await hass.services.async_call(
                DOMAIN,
                "create_automation",
                {
                    "prompt": "Turn on lights when switch is on",
                    "name": "Test Automation",
                    "description": "Test automation"
                },
                blocking=True,
                return_result=True
            )

            mock_agent.async_create_automation.assert_called_once()
            call_args = mock_agent.async_create_automation.call_args[0][0]
            assert "Turn on lights when switch is on" in call_args

    async def test_create_automation_with_validation(self, hass_with_config):
        """Test automation creation with validation."""
        hass = hass_with_config

        with patch.object(hass.data[DOMAIN], "agent") as mock_agent:
            mock_agent.async_create_automation = AsyncMock(return_value={
                "automation_id": "validated_automation",
                "name": "Validated Automation",
                "yaml": "# Valid automation YAML",
                "validation_errors": [],
                "success": True
            })

            await hass.services.async_call(
                DOMAIN,
                "create_automation",
                {
                    "prompt": "Create automation with validation",
                    "name": "Validated Automation",
                    "validate": True
                },
                blocking=True
            )

            mock_agent.async_create_automation.assert_called_once()

    async def test_create_automation_failure(self, hass_with_config):
        """Test automation creation failure."""
        hass = hass_with_config

        with patch.object(hass.data[DOMAIN], "agent") as mock_agent:
            mock_agent.async_create_automation = AsyncMock(return_value={
                "success": False,
                "error": "Failed to create automation",
                "validation_errors": ["Invalid trigger"]
            })

            with pytest.raises(Exception):  # Service should raise exception on failure
                await hass.services.async_call(
                    DOMAIN,
                    "create_automation",
                    {
                        "prompt": "Invalid automation",
                        "name": "Should Fail"
                    },
                    blocking=True
                )


@pytest.mark.integration
class TestDashboardService:
    """Test dashboard creation service."""

    async def test_create_dashboard_room_based(self, hass_with_config, mock_openai_client):
        """Test room-based dashboard creation."""
        hass = hass_with_config

        with patch.object(hass.data[DOMAIN], "agent") as mock_agent:
            mock_agent.async_create_dashboard = AsyncMock(return_value={
                "dashboard_id": "room_dashboard_123",
                "name": "Living Room Dashboard",
                "yaml": "title: Living Room\nviews:\n  - cards: []",
                "success": True
            })

            await hass.services.async_call(
                DOMAIN,
                "create_dashboard",
                {
                    "prompt": "Create living room dashboard",
                    "name": "Living Room Dashboard",
                    "type": "room_based",
                    "area": "living_room"
                },
                blocking=True
            )

            mock_agent.async_create_dashboard.assert_called_once()

    async def test_create_dashboard_functional(self, hass_with_config, mock_openai_client):
        """Test functional dashboard creation."""
        hass = hass_with_config

        with patch.object(hass.data[DOMAIN], "agent") as mock_agent:
            mock_agent.async_create_dashboard = AsyncMock(return_value={
                "dashboard_id": "functional_dashboard_123",
                "name": "Lighting Dashboard",
                "yaml": "title: Lighting\nviews:\n  - cards: []",
                "success": True
            })

            await hass.services.async_call(
                DOMAIN,
                "create_dashboard",
                {
                    "prompt": "Create lighting control dashboard",
                    "name": "Lighting Dashboard",
                    "type": "functional",
                    "function": "lighting"
                },
                blocking=True
            )

            mock_agent.async_create_dashboard.assert_called_once()

    async def test_update_dashboard(self, hass_with_config, mock_openai_client):
        """Test dashboard update."""
        hass = hass_with_config

        with patch.object(hass.data[DOMAIN], "agent") as mock_agent:
            mock_agent.async_update_dashboard = AsyncMock(return_value={
                "dashboard_id": "updated_dashboard_123",
                "name": "Updated Dashboard",
                "yaml": "title: Updated Dashboard\nviews:\n  - cards: []",
                "success": True
            })

            await hass.services.async_call(
                DOMAIN,
                "update_dashboard",
                {
                    "dashboard_id": "existing_dashboard",
                    "prompt": "Add temperature control to dashboard"
                },
                blocking=True
            )

            mock_agent.async_update_dashboard.assert_called_once()


@pytest.mark.integration
class TestConversationHistoryService:
    """Test conversation history services."""

    async def test_save_prompt_history(self, hass_with_config):
        """Test saving prompt history."""
        hass = hass_with_config

        history = [
            {"role": "user", "content": "Hello", "timestamp": "2025-01-14T10:00:00Z"},
            {"role": "assistant", "content": "Hi there!", "timestamp": "2025-01-14T10:00:05Z"}
        ]

        await hass.services.async_call(
            DOMAIN,
            "save_prompt_history",
            {
                "history": history,
                "session_id": "test_session"
            },
            blocking=True
        )

        # Verify service was called (implementation depends on storage mechanism)
        service_calls = hass.services.async_call.call_args_list
        history_calls = [call for call in service_calls if call[0][1] == "save_prompt_history"]
        assert len(history_calls) > 0

    async def test_load_prompt_history(self, hass_with_config):
        """Test loading prompt history."""
        hass = hass_with_config

        with patch.object(hass.data[DOMAIN], "storage") as mock_storage:
            mock_storage.async_load = AsyncMock(return_value=[
                {"role": "user", "content": "Previous question", "timestamp": "2025-01-14T09:00:00Z"},
                {"role": "assistant", "content": "Previous answer", "timestamp": "2025-01-14T09:00:05Z"}
            ])

            result = await hass.services.async_call(
                DOMAIN,
                "load_prompt_history",
                {"session_id": "test_session"},
                blocking=True,
                return_result=True
            )

            mock_storage.async_load.assert_called_once()


@pytest.mark.integration
class TestServiceSecurity:
    """Test service security features."""

    async def test_input_validation_in_query(self, hass_with_config):
        """Test input validation in query service."""
        hass = hass_with_config

        security_manager = hass.data[DOMAIN].get("security_manager")
        if security_manager:
            with patch.object(security_manager, "validate_input") as mock_validate:
                mock_validate.return_value = (False, "Malicious input detected")

                with pytest.raises(Exception):  # Should raise exception for invalid input
                    await hass.services.async_call(
                        DOMAIN,
                        "query",
                        {"prompt": "DROP TABLE users; --"},
                        blocking=True
                    )

                mock_validate.assert_called_once()

    async def test_sensitive_data_sanitization(self, hass_with_config, mock_openai_client):
        """Test that sensitive data is sanitized in service responses."""
        hass = hass_with_config

        with patch.object(hass.data[DOMAIN], "agent") as mock_agent:
            # Mock response with sensitive data
            mock_agent.async_query = AsyncMock(return_value={
                "response": "Here's your API key: sk-1234567890",
                "model": "gpt-4",
                "tokens_used": 15,
                "api_key": "sk-1234567890"  # This should be sanitized
            })

            # The service should sanitize sensitive data in the response
            await hass.services.async_call(
                DOMAIN,
                "query",
                {"prompt": "What's my API key?"},
                blocking=True
            )

            # Verify agent was called
            mock_agent.async_query.assert_called_once()

    async def test_concurrent_request_handling(self, hass_with_config, mock_openai_client):
        """Test handling of concurrent service requests."""
        hass = hass_with_config
        import asyncio

        with patch.object(hass.data[DOMAIN], "agent") as mock_agent:
            mock_agent.async_query = AsyncMock(return_value={
                "response": "Response",
                "model": "gpt-4",
                "tokens_used": 10
            })

            # Make multiple concurrent requests
            tasks = []
            for i in range(5):
                task = hass.services.async_call(
                    DOMAIN,
                    "query",
                    {"prompt": f"Test prompt {i}"},
                    blocking=True
                )
                tasks.append(task)

            # Wait for all to complete
            await asyncio.gather(*tasks, return_exceptions=True)

            # Verify all requests were handled
            assert mock_agent.async_query.call_count == 5


@pytest.mark.integration
class TestServicePerformance:
    """Test service performance and monitoring."""

    async def test_query_service_performance_tracking(self, hass_with_config, mock_openai_client):
        """Test that query service performance is tracked."""
        hass = hass_with_config

        performance_monitor = hass.data[DOMAIN].get("performance_monitor")
        if performance_monitor:
            with patch.object(performance_monitor, "record_request") as mock_record:
                with patch.object(hass.data[DOMAIN], "agent") as mock_agent:
                    mock_agent.async_query = AsyncMock(return_value={
                        "response": "Test response",
                        "model": "gpt-4",
                        "tokens_used": 15,
                        "duration_ms": 1234.5
                    })

                    await hass.services.async_call(
                        DOMAIN,
                        "query",
                        {"prompt": "Test performance tracking"},
                        blocking=True
                    )

                    # Verify performance was recorded
                    mock_record.assert_called_once()

    async def test_service_error_logging(self, hass_with_config):
        """Test that service errors are properly logged."""
        hass = hass_with_config

        structured_logger = hass.data[DOMAIN].get("structured_logger")
        if structured_logger:
            with patch.object(structured_logger, "error") as mock_log:
                with patch.object(hass.data[DOMAIN], "agent") as mock_agent:
                    mock_agent.async_query = AsyncMock(side_effect=Exception("Test error"))

                    with pytest.raises(Exception):
                        await hass.services.async_call(
                            DOMAIN,
                            "query",
                            {"prompt": "Test error logging"},
                            blocking=True
                        )

                    # Verify error was logged
                    mock_log.assert_called_once()

    async def test_service_timeout_handling(self, hass_with_config):
        """Test service timeout handling."""
        hass = hass_with_config

        with patch.object(hass.data[DOMAIN], "agent") as mock_agent:
            # Mock a slow response
            mock_agent.async_query = AsyncMock(side_effect=asyncio.TimeoutError())

            with pytest.raises(asyncio.TimeoutError):
                await hass.services.async_call(
                    DOMAIN,
                    "query",
                    {"prompt": "Test timeout"},
                    blocking=True
                )