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
            
            # Test newer models
            client_o3 = OpenAIClient("test-token", "o3-mini")
            assert client_o3._get_token_parameter() == "max_completion_tokens"
            
            # Test older models
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
            
            client = OpenAIClient("invalid-token", "gpt-3.5-turbo")
            
            with pytest.raises(Exception) as exc_info:
                await client.get_response([{"role": "user", "content": "test"}])
            assert "Invalid OpenAI API key format" in str(exc_info.value)
            
        except ImportError:
            pytest.skip("OpenAIClient not available")