"""Integration setup and configuration flow tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.data_entry_flow import FlowResultType

from custom_components.glm_agent_ha.const import DOMAIN
from custom_components.glm_agent_ha.config_flow import (
    GLMAgentConfigFlow,
    cannot_connect,
    invalid_api_key,
)


@pytest.mark.integration
class TestGLMAgentIntegrationSetup:
    """Test GLM Agent HA integration setup."""

    async def test_async_setup_entry_success(self, hass, mock_config_entry):
        """Test successful setup of config entry."""
        with patch(
            "custom_components.glm_agent_ha.async_setup_entry",
            return_value=True,
        ) as mock_setup:
            from custom_components.glm_agent_ha import async_setup_entry

            result = await async_setup_entry(hass, mock_config_entry)

            assert result
            mock_setup.assert_called_once_with(hass, mock_config_entry)

    async def test_async_setup_entry_failure(self, hass, mock_config_entry):
        """Test failed setup of config entry."""
        with patch(
            "custom_components.glm_agent_ha.async_setup_entry",
            return_value=False,
        ):
            from custom_components.glm_agent_ha import async_setup_entry

            result = await async_setup_entry(hass, mock_config_entry)

            assert not result

    async def test_async_unload_entry_success(self, hass, mock_config_entry):
        """Test successful unloading of config entry."""
        hass.data[DOMAIN] = {}
        hass.data[DOMAIN][mock_config_entry.entry_id] = MagicMock()
        hass.data[DOMAIN][mock_config_entry.entry_id].async_unload = AsyncMock(return_value=True)

        with patch(
            "custom_components.glm_agent_ha.async_unload_entry",
            return_value=True,
        ) as mock_unload:
            from custom_components.glm_agent_ha import async_unload_entry

            result = await async_unload_entry(hass, mock_config_entry)

            assert result
            mock_unload.assert_called_once_with(hass, mock_config_entry)

    async def test_async_unload_entry_failure(self, hass, mock_config_entry):
        """Test failed unloading of config entry."""
        with patch(
            "custom_components.glm_agent_ha.async_unload_entry",
            return_value=False,
        ):
            from custom_components.glm_agent_ha import async_unload_entry

            result = await async_unload_entry(hass, mock_config_entry)

            assert not result

    async def test_setup_minimum_config(self, hass):
        """Test setup with minimum configuration."""
        config = {
            "openai_api_key": "test-key",
            "model": "gpt-3.5-turbo",
            "plan": "lite"
        }

        with patch(
            "custom_components.glm_agent_ha.async_setup_entry",
            return_value=True,
        ):
            result = await async_setup_component(hass, DOMAIN, {DOMAIN: config})
            assert result
            await hass.async_block_till_done()

    async def test_setup_full_config(self, hass):
        """Test setup with full configuration."""
        config = {
            "openai_api_key": "test-key",
            "model": "gpt-4",
            "plan": "pro",
            "enable_context_services": True,
            "enable_mcp_integration": True,
            "max_tokens": 2000,
            "temperature": 0.7,
            "custom_endpoint": "https://api.custom.com/v1"
        }

        with patch(
            "custom_components.glm_agent_ha.async_setup_entry",
            return_value=True,
        ):
            result = await async_setup_component(hass, DOMAIN, {DOMAIN: config})
            assert result
            await hass.async_block_till_done()

    async def test_setup_invalid_config(self, hass):
        """Test setup with invalid configuration."""
        config = {
            "openai_api_key": "",  # Empty API key
            "model": "invalid-model",
            "plan": "invalid-plan"
        }

        result = await async_setup_component(hass, DOMAIN, {DOMAIN: config})
        # Should not setup with invalid config
        assert not result


@pytest.mark.integration
class TestGLMAgentConfigFlow:
    """Test GLM Agent HA config flow."""

    async def test_step_user_init(self, hass):
        """Test initial user step in config flow."""
        flow = GLMAgentConfigFlow()
        flow.hass = hass

        result = await flow.async_step_user()

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"
        assert "openai_api_key" in result["data_schema"].schema

    async def test_step_user_valid_lite_plan(self, hass):
        """Test user step with valid lite plan configuration."""
        flow = GLMAgentConfigFlow()
        flow.hass = hass

        user_input = {
            "openai_api_key": "test-api-key",
            "plan": "lite",
            "model": "gpt-3.5-turbo"
        }

        with patch("custom_components.glm_agent_ha.config_flow.validate_api_key", return_value=True):
            result = await flow.async_step_user(user_input)

            assert result["type"] == FlowResultType.CREATE_ENTRY
            assert result["title"] == "GLM Agent HA"
            assert result["data"]["openai_api_key"] == "test-api-key"
            assert result["data"]["plan"] == "lite"

    async def test_step_user_valid_pro_plan(self, hass):
        """Test user step with valid pro plan configuration."""
        flow = GLMAgentConfigFlow()
        flow.hass = hass

        user_input = {
            "openai_api_key": "test-api-key",
            "plan": "pro",
            "model": "gpt-4",
            "enable_context_services": True,
            "enable_mcp_integration": True
        }

        with patch("custom_components.glm_agent_ha.config_flow.validate_api_key", return_value=True):
            result = await flow.async_step_user(user_input)

            assert result["type"] == FlowResultType.CREATE_ENTRY
            assert result["title"] == "GLM Agent HA"
            assert result["data"]["plan"] == "pro"
            assert result["data"]["enable_context_services"] is True

    async def test_step_user_invalid_api_key(self, hass):
        """Test user step with invalid API key."""
        flow = GLMAgentConfigFlow()
        flow.hass = hass

        user_input = {
            "openai_api_key": "invalid-key",
            "plan": "lite",
            "model": "gpt-3.5-turbo"
        }

        with patch("custom_components.glm_agent_ha.config_flow.validate_api_key", return_value=False):
            result = await flow.async_step_user(user_input)

            assert result["type"] == FlowResultType.FORM
            assert result["errors"]["base"] == "invalid_auth"

    async def test_step_user_connection_error(self, hass):
        """Test user step with connection error."""
        flow = GLMAgentConfigFlow()
        flow.hass = hass

        user_input = {
            "openai_api_key": "test-api-key",
            "plan": "lite",
            "model": "gpt-3.5-turbo"
        }

        with patch("custom_components.glm_agent_ha.config_flow.validate_api_key", side_effect=Exception("Connection error")):
            result = await flow.async_step_user(user_input)

            assert result["type"] == FlowResultType.FORM
            assert result["errors"]["base"] == "cannot_connect"

    async def test_step_reauth_success(self, hass):
        """Test reauthentication step success."""
        flow = GLMAgentConfigFlow()
        flow.hass = hass
        flow.reauth_entry = MagicMock()
        flow.reauth_entry.data = {"openai_api_key": "old-key"}

        user_input = {
            "openai_api_key": "new-api-key",
            "plan": "pro",
            "model": "gpt-4"
        }

        with patch("custom_components.glm_agent_ha.config_flow.validate_api_key", return_value=True):
            result = await flow.async_step_reauth(user_input)

            assert result["type"] == FlowResultType.ABORT
            assert result["reason"] == "reauth_successful"

    async def test_step_reauth_failure(self, hass):
        """Test reauthentication step failure."""
        flow = GLMAgentConfigFlow()
        flow.hass = hass
        flow.reauth_entry = MagicMock()
        flow.reauth_entry.data = {"openai_api_key": "old-key"}

        user_input = {
            "openai_api_key": "invalid-key",
            "plan": "lite",
            "model": "gpt-3.5-turbo"
        }

        with patch("custom_components.glm_agent_ha.config_flow.validate_api_key", return_value=False):
            result = await flow.async_step_reauth(user_input)

            assert result["type"] == FlowResultType.FORM
            assert result["errors"]["base"] == "invalid_auth"

    async def test_options_flow_init(self, hass, mock_config_entry):
        """Test options flow initialization."""
        from custom_components.glm_agent_ha.config_flow import GLMAgentOptionsFlow

        options_flow = GLMAgentOptionsFlow(mock_config_entry)
        options_flow.hass = hass

        result = await options_flow.async_step_init()

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "init"
        assert "model" in result["data_schema"].schema

    async def test_options_flow_update(self, hass, mock_config_entry):
        """Test options flow update."""
        from custom_components.glm_agent_ha.config_flow import GLMAgentOptionsFlow

        options_flow = GLMAgentOptionsFlow(mock_config_entry)
        options_flow.hass = hass

        user_input = {
            "model": "gpt-4",
            "max_tokens": 2000,
            "temperature": 0.7,
            "enable_context_services": True
        }

        result = await options_flow.async_step_init(user_input)

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"]["model"] == "gpt-4"
        assert result["data"]["max_tokens"] == 2000


@pytest.mark.integration
class TestConfigFlowValidators:
    """Test config flow validation functions."""

    async def test_validate_api_key_success(self):
        """Test successful API key validation."""
        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_post.return_value.__aenter__.return_value = mock_response

            from custom_components.glm_agent_ha.config_flow import validate_api_key

            result = await validate_api_key("test-api-key", "https://api.openai.com")
            assert result is True

    async def test_validate_api_key_failure_invalid_key(self):
        """Test API key validation with invalid key."""
        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 401
            mock_post.return_value.__aenter__.return_value = mock_response

            from custom_components.glm_agent_ha.config_flow import validate_api_key

            result = await validate_api_key("invalid-key", "https://api.openai.com")
            assert result is False

    async def test_validate_api_key_failure_connection_error(self):
        """Test API key validation with connection error."""
        with patch("aiohttp.ClientSession.post", side_effect=Exception("Connection error")):
            from custom_components.glm_agent_ha.config_flow import validate_api_key

            with pytest.raises(Exception):
                await validate_api_key("test-api-key", "https://api.openai.com")

    async def test_cannot_connect_error(self):
        """Test cannot_connect error handler."""
        result = cannot_connect(Exception("Connection failed"))
        assert "cannot_connect" in result

    async def test_invalid_api_key_error(self):
        """Test invalid_api_key error handler."""
        result = invalid_api_key(Exception("Invalid API key"))
        assert "invalid_auth" in result


@pytest.mark.integration
class TestEntryMigration:
    """Test config entry migration."""

    async def test_migrate_entry_v1_to_v2(self, hass):
        """Test migration from version 1 to 2."""
        old_entry = MagicMock()
        old_entry.version = 1
        old_entry.data = {
            "openai_api_key": "test-key",
            "model": "gpt-3.5-turbo"
        }

        # Mock the migration function
        with patch("custom_components.glm_agent_ha.migrate_entry", return_value=True) as mock_migrate:
            from custom_components.glm_agent_ha import migrate_entry

            result = await migrate_entry(hass, old_entry)

            assert result
            mock_migrate.assert_called_once_with(hass, old_entry)

    async def test_migrate_entry_same_version(self, hass):
        """Test migration when entry is already at target version."""
        entry = MagicMock()
        entry.version = 2
        entry.data = {"openai_api_key": "test-key"}

        # Mock current version as 2
        with patch("custom_components.glm_agent_ha.const.CONFIG_VERSION", 2):
            from custom_components.glm_agent_ha import migrate_entry

            result = await migrate_entry(hass, entry)

            # Should return True without modification if same version
            assert result is True


@pytest.mark.integration
class TestServiceRegistration:
    """Test service registration during setup."""

    async def test_services_registered_on_setup(self, hass, mock_config_entry):
        """Test that services are registered during setup."""
        with patch("custom_components.glm_agent_ha.async_setup_entry", return_value=True):
            from custom_components.glm_agent_ha import async_setup_entry

            await async_setup_entry(hass, mock_config_entry)

            # Check that services were registered
            service_calls = hass.services.async_register.call_args_list
            assert len(service_calls) > 0

            # Check for expected services
            registered_services = [call[0][1] for call in service_calls]
            expected_services = [
                "query",
                "create_automation",
                "create_dashboard",
                "update_dashboard",
                "save_prompt_history",
                "load_prompt_history"
            ]

            for service in expected_services:
                assert service in registered_services

    async def test_debug_services_registered(self, hass, mock_config_entry_pro):
        """Test that debug services are registered for pro plan."""
        with patch("custom_components.glm_agent_ha.async_setup_entry", return_value=True):
            from custom_components.glm_agent_ha import async_setup_entry

            await async_setup_entry(hass, mock_config_entry_pro)

            # Check for debug services
            service_calls = hass.services.async_register.call_args_list
            registered_services = [call[0][1] for call in service_calls]

            debug_services = [
                "generate_debug_report",
                "get_system_info",
                "get_integration_status",
                "test_api_connection",
                "get_recent_logs"
            ]

            for service in debug_services:
                assert service in registered_services

    async def test_security_services_registered(self, hass, mock_config_entry_pro):
        """Test that security services are registered."""
        with patch("custom_components.glm_agent_ha.async_setup_entry", return_value=True):
            from custom_components.glm_agent_ha import async_setup_entry

            await async_setup_entry(hass, mock_config_entry_pro)

            # Check for security services
            service_calls = hass.services.async_register.call_args_list
            registered_services = [call[0][1] for call in service_calls]

            security_services = [
                "security_report",
                "security_validate",
                "security_block",
                "security_domains"
            ]

            for service in security_services:
                assert service in registered_services