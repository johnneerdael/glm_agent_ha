"""Test structured output enforcement for GLM AI Agent HA integration."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.glm_agent_ha.agent import OpenAIClient, AiAgentHaAgent


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock()
    hass.config.path.return_value = "/config"
    hass.states.async_all.return_value = []
    hass.states.get.return_value = None
    return hass


@pytest.fixture
def agent_config():
    """Create a basic agent configuration."""
    return {
        "ai_provider": "openai",
        "openai_token": "test_token_12345678901234567890",
        "models": {"openai": "GLM-4.6"}
    }


@pytest.fixture
def agent(mock_hass, agent_config):
    """Create an AI agent instance."""
    return AiAgentHaAgent(mock_hass, agent_config)


@pytest.fixture
def openai_client():
    """Create an OpenAI client instance."""
    return OpenAIClient("test_token_12345678901234567890", "GLM-4.6")


class TestStructuredOutput:
    """Test structured output enforcement."""

    @pytest.mark.asyncio
    async def test_openai_client_with_response_format(self, openai_client):
        """Test that OpenAIClient properly handles response_format parameter."""
        messages = [{"role": "user", "content": "test message"}]
        response_format = {"type": "json_object"}
        
        mock_response = {
            "choices": [
                {
                    "message": {
                        "content": '{"request_type": "final_response", "response": "test response"}'
                    }
                }
            ]
        }
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value.status = 200
            mock_post.return_value.__aenter__.return_value.text.return_value = json.dumps(mock_response)
            
            response = await openai_client.get_response(messages, response_format=response_format)
            
            # Verify the call included response_format in payload
            call_args = mock_post.call_args
            payload = json.loads(call_args[1]['json'])
            assert "response_format" in payload
            assert payload["response_format"] == response_format
            assert response == '{"request_type": "final_response", "response": "test response"}'

    @pytest.mark.asyncio
    async def test_openai_client_without_response_format(self, openai_client):
        """Test that OpenAIClient works without response_format parameter."""
        messages = [{"role": "user", "content": "test message"}]
        
        mock_response = {
            "choices": [
                {
                    "message": {
                        "content": "Plain text response"
                    }
                }
            ]
        }
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value.status = 200
            mock_post.return_value.__aenter__.return_value.text.return_value = json.dumps(mock_response)
            
            response = await openai_client.get_response(messages)
            
            # Verify the call did not include response_format
            call_args = mock_post.call_args
            payload = json.loads(call_args[1]['json'])
            assert "response_format" not in payload
            assert response == "Plain text response"

    @pytest.mark.asyncio
    async def test_process_query_with_structure_enforcement(self, agent):
        """Test that process_query enforces JSON mode when structure is provided."""
        structure = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "value": {"type": "number"}
            },
            "required": ["name", "value"]
        }
        
        # Mock the AI client to return structured JSON
        mock_response = json.dumps({
            "request_type": "final_response",
            "response": {"name": "test", "value": 42}
        })
        
        agent.ai_client.get_response = AsyncMock(return_value=mock_response)
        
        result = await agent.process_query(
            "Generate a name and number",
            structure=structure
        )
        
        # Verify JSON mode was enforced
        agent.ai_client.get_response.assert_called_once()
        call_args = agent.ai_client.get_response.call_args
        assert call_args[1]['response_format'] == {"type": "json_object"}
        
        # Verify the result
        assert result["success"] is True
        assert "answer" in result

    @pytest.mark.asyncio
    async def test_process_query_schema_instruction_injection(self, agent):
        """Test that schema instruction is injected when structure is provided."""
        structure = {
            "type": "object",
            "properties": {"result": {"type": "string"}},
            "required": ["result"]
        }
        
        # Mock the AI client
        agent.ai_client.get_response = AsyncMock(return_value='{"request_type": "final_response", "response": {"result": "success"}}')
        
        await agent.process_query("Test query", structure=structure)
        
        # Check that schema instruction was added to conversation
        schema_instruction_found = False
        for message in agent.conversation_history:
            if message.get("role") == "system" and "You MUST return a single valid JSON object" in message.get("content", ""):
                schema_instruction_found = True
                # Verify the schema is included in the instruction
                assert json.dumps(structure) in message.get("content", "")
                break
        
        assert schema_instruction_found, "Schema instruction should be injected into conversation"

    @pytest.mark.asyncio
    async def test_process_query_corrective_retry_on_json_error(self, agent):
        """Test corrective retry when JSON parsing fails with structure enforcement."""
        structure = {
            "type": "object", 
            "properties": {"result": {"type": "string"}},
            "required": ["result"]
        }
        
        # First call returns invalid JSON, second call returns valid JSON
        agent.ai_client.get_response = AsyncMock(side_effect=[
            "This is not valid JSON despite JSON mode request",
            '{"request_type": "final_response", "response": {"result": "success"}}'
        ])
        
        result = await agent.process_query("Test query", structure=structure)
        
        # Verify two attempts were made
        assert agent.ai_client.get_response.call_count == 2
        
        # Verify corrective instruction was added
        corrective_instruction_found = False
        for message in agent.conversation_history:
            if (message.get("role") == "system" and 
                "The previous response was not valid JSON" in message.get("content", "")):
                corrective_instruction_found = True
                break
        
        assert corrective_instruction_found, "Corrective instruction should be added after JSON parsing failure"
        
        # Verify final result is successful
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_process_query_without_structure(self, agent):
        """Test that process_query works normally without structure parameter."""
        # Mock the AI client to return regular response
        mock_response = json.dumps({
            "request_type": "final_response",
            "response": "This is a regular response"
        })
        
        agent.ai_client.get_response = AsyncMock(return_value=mock_response)
        
        result = await agent.process_query("Test query without structure")
        
        # Verify JSON mode was NOT enforced
        agent.ai_client.get_response.assert_called_once()
        call_args = agent.ai_client.get_response.call_args
        assert call_args[1]['response_format'] is None
        
        # Verify the result
        assert result["success"] is True
        assert result["answer"] == '{"request_type": "final_response", "response": "This is a regular response"}'

    @pytest.mark.asyncio
    async def test_integration_query_service_with_structure(self, mock_hass, agent_config):
        """Test that the query service properly forwards the structure parameter."""
        from custom_components.glm_agent_ha import async_setup_entry
        from homeassistant.core import ServiceCall
        import pytest
        
        # Create config entry
        config_entry = MagicMock()
        config_entry.version = 1
        config_entry.data = agent_config
        
        # Setup integration
        with patch('custom_components.glm_agent_ha.AiAgentHaAgent') as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent_class.return_value = mock_agent
            
            # Configure mock agent to return structured response
            mock_agent.process_query.return_value = {
                "success": True,
                "answer": '{"result": "structured_data"}'
            }
            
            # Setup hass data
            mock_hass.data = {"glm_agent_ha": {"agents": {"openai": mock_agent}, "configs": {"openai": agent_config}}}
            mock_hass.services.async_register = MagicMock()
            mock_hass.bus.async_fire = MagicMock()
            
            # Setup entry
            await async_setup_entry(mock_hass, config_entry)
            
            # Get the registered query service handler
            service_calls = []
            def capture_service_call(domain, service, handler):
                if service == "query":
                    service_calls.append(handler)
            
            mock_hass.services.async_register.side_effect = capture_service_call
            
            # Re-register to capture the handler
            await async_setup_entry(mock_hass, config_entry)
            
            # Create a service call with structure
            service_call = MagicMock()
            service_call.data = {
                "prompt": "Generate structured data",
                "structure": {
                    "type": "object",
                    "properties": {"result": {"type": "string"}},
                    "required": ["result"]
                }
            }
            service_call.context = MagicMock()
            service_call.context.user_id = "test_user"
            
            # Call the service handler directly
            if service_calls:
                await service_calls[-1](service_call)
                
                # Verify the structure parameter was passed to process_query
                mock_agent.process_query.assert_called_once()
                call_args = mock_agent.process_query.call_args
                assert "structure" in call_args[1]
                assert call_args[1]["structure"] == service_call.data["structure"]