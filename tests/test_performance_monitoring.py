"""Test performance monitoring functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import time
from datetime import datetime, timedelta

from custom_components.glm_agent_ha.const import DOMAIN


@pytest.mark.performance
class TestPerformanceMonitor:
    """Test performance monitoring functionality."""

    async def test_request_metrics_recording(self, hass_with_config):
        """Test recording of request metrics."""
        hass = hass_with_config
        performance_monitor = hass.data[DOMAIN].get("performance_monitor")

        if performance_monitor:
            # Record a request
            performance_monitor.record_request(
                request_id="test_req_123",
                request_type="query",
                provider="openai",
                model="gpt-4",
                duration_ms=1234.5,
                success=True,
                tokens_used=15,
                input_length=25,
                output_length=50
            )

            # Check that metrics were recorded
            metrics = performance_monitor.get_metrics()
            assert metrics["total_requests"] == 1
            assert metrics["successful_requests"] == 1
            assert metrics["failed_requests"] == 0

    async def test_failed_request_metrics(self, hass_with_config):
        """Test recording of failed request metrics."""
        hass = hass_with_config
        performance_monitor = hass.data[DOMAIN].get("performance_monitor")

        if performance_monitor:
            # Record a failed request
            performance_monitor.record_request(
                request_id="test_req_failed",
                request_type="automation",
                provider="openai",
                model="gpt-4",
                duration_ms=5000.0,
                success=False,
                error_type="TimeoutError",
                input_length=100
            )

            # Check that failure metrics were recorded
            metrics = performance_monitor.get_metrics()
            assert metrics["total_requests"] == 1
            assert metrics["successful_requests"] == 0
            assert metrics["failed_requests"] == 1

    async def test_performance_aggregation(self, hass_with_config):
        """Test performance metrics aggregation."""
        hass = hass_with_config
        performance_monitor = hass.data[DOMAIN].get("performance_monitor")

        if performance_monitor:
            # Record multiple requests
            durations = [1000.0, 1500.0, 1200.0, 800.0, 2000.0]
            for i, duration in enumerate(durations):
                performance_monitor.record_request(
                    request_id=f"req_{i}",
                    request_type="query",
                    provider="openai",
                    model="gpt-4",
                    duration_ms=duration,
                    success=True
                )

            # Check aggregated metrics
            metrics = performance_monitor.get_metrics()
            assert metrics["total_requests"] == 5

            # Check average duration
            expected_avg = sum(durations) / len(durations)
            assert abs(metrics["average_duration_ms"] - expected_avg) < 0.01

            # Check min/max
            assert metrics["min_duration_ms"] == min(durations)
            assert metrics["max_duration_ms"] == max(durations)

    async def test_performance_by_request_type(self, hass_with_config):
        """Test performance metrics by request type."""
        hass = hass_with_config
        performance_monitor = hass.data[DOMAIN].get("performance_monitor")

        if performance_monitor:
            # Record different request types
            performance_monitor.record_request(
                request_id="query_1", request_type="query", provider="openai",
                model="gpt-4", duration_ms=1000.0, success=True
            )
            performance_monitor.record_request(
                request_id="auto_1", request_type="automation", provider="openai",
                model="gpt-4", duration_ms=2000.0, success=True
            )
            performance_monitor.record_request(
                request_id="dash_1", request_type="dashboard", provider="openai",
                model="gpt-4", duration_ms=1500.0, success=True
            )

            # Get metrics by type
            metrics_by_type = performance_monitor.get_metrics_by_type()

            assert "query" in metrics_by_type
            assert "automation" in metrics_by_type
            assert "dashboard" in metrics_by_type

            assert metrics_by_type["query"]["total_requests"] == 1
            assert metrics_by_type["automation"]["total_requests"] == 1
            assert metrics_by_type["dashboard"]["total_requests"] == 1

    async def test_performance_by_provider(self, hass_with_config):
        """Test performance metrics by provider."""
        hass = hass_with_config
        performance_monitor = hass.data[DOMAIN].get("performance_monitor")

        if performance_monitor:
            # Record requests from different providers
            performance_monitor.record_request(
                request_id="openai_1", request_type="query", provider="openai",
                model="gpt-4", duration_ms=1200.0, success=True
            )
            performance_monitor.record_request(
                request_id="claude_1", request_type="query", provider="anthropic",
                model="claude-3", duration_ms=800.0, success=True
            )

            # Get metrics by provider
            metrics_by_provider = performance_monitor.get_metrics_by_provider()

            assert "openai" in metrics_by_provider
            assert "anthropic" in metrics_by_provider

            assert metrics_by_provider["openai"]["total_requests"] == 1
            assert metrics_by_provider["anthropic"]["total_requests"] == 1

    async def test_performance_trends(self, hass_with_config):
        """Test performance trend analysis."""
        hass = hass_with_config
        performance_monitor = hass.data[DOMAIN].get("performance_monitor")

        if performance_monitor:
            base_time = datetime.now()

            # Record requests over time
            for i in range(10):
                test_time = base_time + timedelta(minutes=i)
                with patch('datetime.datetime') as mock_datetime:
                    mock_datetime.now.return_value = test_time

                    performance_monitor.record_request(
                        request_id=f"trend_req_{i}",
                        request_type="query",
                        provider="openai",
                        model="gpt-4",
                        duration_ms=1000.0 + (i * 100),  # Increasing duration
                        success=True
                    )

            # Get trends
            trends = performance_monitor.get_performance_trends(hours=1)

            assert "duration_trend" in trends
            assert "request_rate_trend" in trends
            assert "error_rate_trend" in trends

    async def test_performance_alerts(self, hass_with_config):
        """Test performance alerting."""
        hass = hass_with_config
        performance_monitor = hass.data[DOMAIN].get("performance_monitor")

        if performance_monitor:
            # Record slow requests that should trigger alerts
            slow_durations = [5000.0, 6000.0, 7000.0, 8000.0, 9000.0]
            for i, duration in enumerate(slow_durations):
                performance_monitor.record_request(
                    request_id=f"slow_req_{i}",
                    request_type="query",
                    provider="openai",
                    model="gpt-4",
                    duration_ms=duration,
                    success=True
                )

            # Check for alerts
            alerts = performance_monitor.get_performance_alerts()

            # Should have alerts for slow response times
            slow_alerts = [alert for alert in alerts if "slow" in alert["type"].lower()]
            assert len(slow_alerts) > 0, "Should generate alerts for slow requests"

    async def test_performance_thresholds(self, hass_with_config):
        """Test performance threshold monitoring."""
        hass = hass_with_config
        performance_monitor = hass.data[DOMAIN].get("performance_monitor")

        if performance_monitor:
            # Set custom thresholds
            performance_monitor.set_thresholds({
                "max_response_time_ms": 2000.0,
                "max_error_rate_percent": 10.0,
                "min_success_rate_percent": 90.0
            })

            # Record a request that exceeds threshold
            performance_monitor.record_request(
                request_id="threshold_req",
                request_type="query",
                provider="openai",
                model="gpt-4",
                duration_ms=3000.0,  # Exceeds 2000ms threshold
                success=True
            )

            # Check threshold violations
            violations = performance_monitor.check_threshold_violations()

            assert len(violations) > 0, "Should detect threshold violations"
            response_time_violations = [v for v in violations if "response_time" in v["type"]]
            assert len(response_time_violations) > 0

    async def test_concurrent_request_tracking(self, hass_with_config):
        """Test tracking of concurrent requests."""
        hass = hass_with_config
        performance_monitor = hass.data[DOMAIN].get("performance_monitor")

        if performance_monitor:
            import asyncio

            # Start multiple concurrent requests
            async def simulate_request(request_id, duration):
                performance_monitor.start_request(request_id, "query", "openai", "gpt-4")
                await asyncio.sleep(duration)
                performance_monitor.end_request(request_id, duration * 1000, True)

            # Run concurrent requests
            tasks = [
                simulate_request(f"concurrent_{i}", 0.1 + (i * 0.05))
                for i in range(5)
            ]

            await asyncio.gather(*tasks)

            # Check that all requests were tracked
            metrics = performance_monitor.get_metrics()
            assert metrics["total_requests"] == 5

            # Check concurrent request statistics
            concurrent_stats = performance_monitor.get_concurrent_stats()
            assert "max_concurrent" in concurrent_stats
            assert concurrent_stats["max_concurrent"] <= 5

    async def test_performance_memory_management(self, hass_with_config):
        """Test performance monitoring memory management."""
        hass = hass_with_config
        performance_monitor = hass.data[DOMAIN].get("performance_monitor")

        if performance_monitor:
            # Record many requests to test memory limits
            for i in range(2000):  # Exceed typical limits
                performance_monitor.record_request(
                    request_id=f"memory_test_{i}",
                    request_type="query",
                    provider="openai",
                    model="gpt-4",
                    duration_ms=1000.0,
                    success=True
                )

            # Check that old metrics are cleaned up
            metrics = performance_monitor.get_metrics()
            # Should not have unbounded growth
            assert metrics["total_requests"] < 2000, "Should limit memory usage"

    async def test_performance_export_import(self, hass_with_config):
        """Test performance data export and import."""
        hass = hass_with_config
        performance_monitor = hass.data[DOMAIN].get("performance_monitor")

        if performance_monitor:
            # Record some test data
            for i in range(10):
                performance_monitor.record_request(
                    request_id=f"export_test_{i}",
                    request_type="query",
                    provider="openai",
                    model="gpt-4",
                    duration_ms=1000.0 + (i * 100),
                    success=i % 5 != 0  # Some failures
                )

            # Export data
            exported_data = performance_monitor.export_metrics()

            assert "metrics" in exported_data
            assert "metadata" in exported_data
            assert "export_timestamp" in exported_data
            assert exported_data["metrics"]["total_requests"] == 10

            # Create new monitor and import data
            new_monitor = type(performance_monitor)(hass)
            new_monitor.import_metrics(exported_data)

            # Verify imported data
            imported_metrics = new_monitor.get_metrics()
            assert imported_metrics["total_requests"] == 10


@pytest.mark.performance
class TestPerformanceServices:
    """Test performance monitoring services."""

    async def test_performance_stats_service(self, hass_with_config):
        """Test performance statistics service."""
        hass = hass_with_config

        # Record some test data first
        performance_monitor = hass.data[DOMAIN].get("performance_monitor")
        if performance_monitor:
            performance_monitor.record_request(
                request_id="service_test",
                request_type="query",
                provider="openai",
                model="gpt-4",
                duration_ms=1500.0,
                success=True,
                tokens_used=25
            )

        result = await hass.services.async_call(
            DOMAIN,
            "performance_stats",
            {},
            blocking=True,
            return_result=True
        )

        assert "session_metrics" in result
        assert "aggregated_stats" in result
        assert "performance_health" in result
        assert result["session_metrics"]["total_requests"] >= 0

    async def test_performance_trends_service(self, hass_with_config):
        """Test performance trends service."""
        hass = hass_with_config

        result = await hass.services.async_call(
            DOMAIN,
            "performance_trends",
            {"hours": 24},
            blocking=True,
            return_result=True
        )

        assert "trends" in result
        assert "period_hours" in result
        assert result["period_hours"] == 24
        assert "health_indicators" in result

    async def test_performance_alerts_service(self, hass_with_config):
        """Test performance alerts service."""
        hass = hass_with_config

        result = await hass.services.async_call(
            DOMAIN,
            "performance_alerts",
            {"severity": "high"},
            blocking=True,
            return_result=True
        )

        assert "alerts" in result
        assert isinstance(result["alerts"], list)
        assert "alert_count" in result
        assert "last_check" in result

    async def test_performance_reset_service(self, hass_with_config):
        """Test performance metrics reset service."""
        hass = hass_with_config

        # Record test data
        performance_monitor = hass.data[DOMAIN].get("performance_monitor")
        if performance_monitor:
            performance_monitor.record_request(
                request_id="reset_test",
                request_type="query",
                provider="openai",
                model="gpt-4",
                duration_ms=1000.0,
                success=True
            )

            # Verify data exists
            metrics_before = performance_monitor.get_metrics()
            assert metrics_before["total_requests"] > 0

            # Reset metrics
            await hass.services.async_call(
                DOMAIN,
                "performance_reset",
                {},
                blocking=True
            )

            # Verify data was reset
            metrics_after = performance_monitor.get_metrics()
            assert metrics_after["total_requests"] == 0

    async def test_performance_export_service(self, hass_with_config):
        """Test performance data export service."""
        hass = hass_with_config

        result = await hass.services.async_call(
            DOMAIN,
            "performance_export",
            {"format": "json"},
            blocking=True,
            return_result=True
        )

        assert "data" in result
        assert "format" in result
        assert "exported_at" in result
        assert result["format"] == "json"

    async def test_performance_health_service(self, hass_with_config):
        """Test performance health check service."""
        hass = hass_with_config

        result = await hass.services.async_call(
            DOMAIN,
            "performance_health",
            {},
            blocking=True,
            return_result=True
        )

        assert "overall_health" in result
        assert "health_score" in result
        assert "recommendations" in result
        assert "issues" in result
        assert isinstance(result["health_score"], (int, float))
        assert 0 <= result["health_score"] <= 100


@pytest.mark.performance
class TestPerformanceIntegration:
    """Test performance monitoring integration."""

    async def test_performance_in_query_service(self, hass_with_config, mock_openai_client):
        """Test performance monitoring integration in query service."""
        hass = hass_with_config

        performance_monitor = hass.data[DOMAIN].get("performance_monitor")
        if performance_monitor:
            with patch.object(hass.data[DOMAIN], "agent") as mock_agent:
                mock_agent.async_query = AsyncMock(return_value={
                    "response": "Test response",
                    "model": "gpt-4",
                    "tokens_used": 15,
                    "duration_ms": 1234.5
                })

                # Call query service
                await hass.services.async_call(
                    DOMAIN,
                    "query",
                    {"prompt": "Test performance tracking"},
                    blocking=True
                )

                # Check that performance was recorded
                metrics = performance_monitor.get_metrics()
                assert metrics["total_requests"] >= 1

    async def test_performance_impact_on_response_time(self, hass_with_config):
        """Test that performance monitoring doesn't significantly impact response time."""
        hass = hass_with_config

        performance_monitor = hass.data[DOMAIN].get("performance_monitor")
        if performance_monitor:
            # Measure time with monitoring
            start_time = time.time()

            for i in range(100):
                performance_monitor.record_request(
                    request_id=f"impact_test_{i}",
                    request_type="query",
                    provider="openai",
                    model="gpt-4",
                    duration_ms=1000.0,
                    success=True
                )

            monitoring_time = time.time() - start_time

            # Should complete quickly (less than 1 second for 100 operations)
            assert monitoring_time < 1.0, f"Performance monitoring took too long: {monitoring_time}s"

    async def test_performance_with_large_responses(self, hass_with_config):
        """Test performance monitoring with large responses."""
        hass = hass_with_config

        performance_monitor = hass.data[DOMAIN].get("performance_monitor")
        if performance_monitor:
            # Record metrics for large response
            performance_monitor.record_request(
                request_id="large_response",
                request_type="dashboard",
                provider="openai",
                model="gpt-4",
                duration_ms=5000.0,
                success=True,
                tokens_used=2000,  # Large response
                input_length=50,
                output_length=4000
            )

            # Check that large response metrics are handled correctly
            metrics = performance_monitor.get_metrics()
            assert metrics["total_tokens"] == 2000
            assert metrics["average_output_length"] == 4000

    async def test_performance_error_recovery(self, hass_with_config):
        """Test performance monitoring during error conditions."""
        hass = hass_with_config

        performance_monitor = hass.data[DOMAIN].get("performance_monitor")
        if performance_monitor:
            # Record mix of successes and failures
            for i in range(20):
                success = i % 4 != 0  # 75% success rate
                performance_monitor.record_request(
                    request_id=f"error_recovery_{i}",
                    request_type="query",
                    provider="openai",
                    model="gpt-4",
                    duration_ms=1000.0,
                    success=success,
                    error_type=None if success else "TimeoutError"
                )

            # Check error rate calculation
            metrics = performance_monitor.get_metrics()
            expected_success_rate = 15 / 20 * 100  # 75%
            assert abs(metrics["success_rate_percent"] - expected_success_rate) < 1

            # Should detect elevated error rate
            alerts = performance_monitor.get_performance_alerts()
            error_alerts = [alert for alert in alerts if "error_rate" in alert["type"]]
            if metrics["success_rate_percent"] < 90:  # If error rate is high
                assert len(error_alerts) > 0, "Should alert on high error rate"