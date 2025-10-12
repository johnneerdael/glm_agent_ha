"""Tests for AI client implementations."""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, patch, Mock
import sys
import os

# Add the parent directory to the path for direct imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

class TestOpenAIClient:
    """Test OpenAI client functionality."""

    def test_openai_client_initialization(self):
        """Test OpenAIClient initialization."""
        try:
            from custom_components.glm_agent_ha.agent import OpenAIClient
            
            client = OpenAIClient("test-token", "gpt-3.5-turbo")
            assert client.token == "test-token"
            assert client.model == "gpt-3.5-turbo"
        except ImportError:
            pytest.skip("OpenAIClient not available")

    def test_openai_token_parameter_detection(self):
        """Test OpenAI token parameter detection."""
        try:
            from custom_components.glm_agent_ha.agent import OpenAIClient
            
            # Test GLM models (should use max_completion_tokens)
            client_glm46 = OpenAIClient("test-token", "GLM-4.6")
            assert client_glm46._get_token_parameter() == "max_completion_tokens"
            
            client_glm45 = OpenAIClient("test-token", "GLM-4.5")
            assert client_glm45._get_token_parameter() == "max_completion_tokens"
            
            client_glm45_air = OpenAIClient("test-token", "GLM-4.5-air")
            assert client_glm45_air._get_token_parameter() == "max_completion_tokens"
            
            # Test older models (should use max_tokens)
            client_gpt = OpenAIClient("test-token", "gpt-3.5-turbo")
            assert client_gpt._get_token_parameter() == "max_tokens"
            
        except ImportError:
            pytest.skip("OpenAIClient not available")

    def test_openai_restricted_model_detection(self):
        """Test OpenAI restricted model detection."""
        try:
            from custom_components.glm_agent_ha.agent import OpenAIClient
            
            # Test restricted models
            client_o3 = OpenAIClient("test-token", "o3-mini")
            assert client_o3._is_restricted_model() is True
            
            # Test unrestricted models
            client_gpt = OpenAIClient("test-token", "gpt-3.5-turbo")
            assert client_gpt._is_restricted_model() is False
            
        except ImportError:
            pytest.skip("OpenAIClient not available")

    @pytest.mark.asyncio
    async def test_openai_client_invalid_token(self):
        """Test OpenAIClient with invalid token."""
        try:
            from custom_components.glm_agent_ha.agent import OpenAIClient
            
            # Test with empty token
            client = OpenAIClient("", "gpt-3.5-turbo")
            
            with pytest.raises(Exception) as exc_info:
                await client.get_response([{"role": "user", "content": "test"}])
            assert "API key is required" in str(exc_info.value)
            
            # Test with too short token
            client_short = OpenAIClient("short", "gpt-3.5-turbo")
            
            with pytest.raises(Exception) as exc_info:
                await client_short.get_response([{"role": "user", "content": "test"}])
            assert "API key appears to be too short" in str(exc_info.value)
            
        except ImportError:
            pytest.skip("OpenAIClient not available")