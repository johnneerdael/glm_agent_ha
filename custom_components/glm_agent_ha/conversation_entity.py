"""GLM Agent HA Conversation Entity for Home Assistant.

This module provides a proper ConversationEntity implementation that integrates
with Home Assistant's conversation system and allows GLM AI Agent to handle
user queries through the conversation interface.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Literal, Optional, Union

from homeassistant.components import conversation as ha_conversation
from homeassistant.components.conversation import ConversationInput, ConversationResult
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, Context
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import ulid

from .agent import AiAgentHaAgent
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class GLMAgentConversationEntity(ha_conversation.AbstractConversationAgent, ha_conversation.ConversationEntity):
    """GLM Agent Conversation Entity that extends Home Assistant's ConversationEntity.

    This entity provides a proper conversation interface for the GLM AI Agent,
    allowing it to be registered with Home Assistant's conversation system
    and handle user queries through the standard conversation interface.
    """

    def __init__(self, hass: HomeAssistant, config: ConfigType, entry_id: str) -> None:
        """Initialize the GLM Agent conversation entity."""
        super().__init__(hass)
        self.hass = hass
        self.config = config
        self.entry_id = entry_id
        # Entity attributes
        self._attr_has_entity_name = True
        self._attr_name = "GLM Agent"
        self._attr_unique_id = f"conversation_{entry_id}"
        self._attr_should_poll = False

        # Device info for proper integration
        self._attr_device_info = dr.DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name="GLM Agent HA",
            manufacturer="Zhipu AI",
            model="GLM Agent",
            entry_type=dr.DeviceEntryType.SERVICE,
        )

        # Initialize the AI agent
        self._agent: Optional[AiAgentHaAgent] = None
        self._initialize_agent()

    def _initialize_agent(self) -> None:
        """Initialize the AI agent."""
        try:
            self._agent = AiAgentHaAgent(self.hass, self.config)
            _LOGGER.info("GLM Agent conversation entity initialized for entry: %s", self.entry_id)
        except Exception as e:
            _LOGGER.error("Failed to initialize GLM Agent conversation entity: %s", e)
            self._agent = None

    @property
    def supported_languages(self) -> List[str] | Literal["*"]:
        """Return supported languages for this conversation agent.
        
        Returns "*" to indicate all languages are supported since GLM models
        are multilingual.
        """
        return ["en", "en-US", "zh", "zh-CN", "zh-TW", "*"]

    @property
    def available(self) -> bool:
        """Return True if the conversation entity is available."""
        return self._agent is not None

    async def _async_handle_message(
        self,
        user_input: ConversationInput,
    ) -> ConversationResult:
        """Handle a conversation message.

        This is the main method that processes user input through the GLM AI Agent
        and returns a conversation result that can be used by Home Assistant's
        conversation system.

        Args:
            user_input: The conversation input containing the user's message,
                       context, and other metadata.

        Returns:
            ConversationResult: The result of processing the message.
        """
        # Comprehensive input validation
        validation_result = self._validate_conversation_input(user_input)
        if not validation_result["valid"]:
            return ConversationResult(
                response=self._create_error_response(
                    validation_result["error"],
                    error_type="validation_error"
                ),
                conversation_id=user_input.conversation_id,
            )

        if not self._agent:
            # Return an error response if the agent is not initialized
            return ConversationResult(
                response=self._create_error_response(
                    "GLM Agent is not properly initialized",
                    error_type="agent_not_initialized"
                ),
                conversation_id=user_input.conversation_id,
            )

        try:
            # Get context information from Home Assistant
            context_info = await self._get_assistant_context(user_input)

            # Extract and validate message text
            message_text = user_input.text.strip()
            if not message_text:
                return ConversationResult(
                    response=self._create_error_response(
                        "Empty message received",
                        error_type="empty_message"
                    ),
                    conversation_id=user_input.conversation_id,
                )

            user_id = user_input.context.user_id if user_input.context else None
            _LOGGER.debug(
                "Processing conversation message: %s (language: %s, user: %s)",
                message_text[:100] + "..." if len(message_text) > 100 else message_text,
                user_input.language,
                user_id,
            )

            # Process the query with GLM agent
            result = await self._agent.process_query(
                user_query=message_text
            )

            if result and result.get("success"):
                # Create successful response
                response_text = result.get("answer", "I'm sorry, I couldn't process your request.")
                conversation_result = ConversationResult(
                    response=self._create_success_response(response_text),
                    conversation_id=user_input.conversation_id,
                )

                # Broadcast conversation update via secure WebSocket
                await self._broadcast_conversation_update(
                    message_text, response_text, user_input.conversation_id
                )

                _LOGGER.debug("Successfully processed conversation message")
                return conversation_result
            else:
                # Handle processing error
                error_msg = result.get("error", "I'm sorry, I couldn't process your request.")
                _LOGGER.warning("GLM Agent processing failed: %s", error_msg)
                
                return ConversationResult(
                    response=self._create_error_response(
                        error_msg,
                        error_type="processing_error"
                    ),
                    conversation_id=user_input.conversation_id,
                )

        except Exception as e:
            _LOGGER.error("Error processing conversation message: %s", e)
            return ConversationResult(
                response=self._create_error_response(
                    f"An unexpected error occurred: {str(e)}",
                    error_type="unexpected_error"
                ),
                conversation_id=user_input.conversation_id,
            )

    async def _get_assistant_context(self, user_input: ConversationInput) -> Dict[str, Any]:
        """Get assistant context information for the GLM agent.
        
        Args:
            user_input: The conversation input containing context information.
            
        Returns:
            Dictionary containing context information.
        """
        context_info = {
            "conversation_id": user_input.conversation_id,
            "language": user_input.language,
            "device_id": user_input.device_id,
            "user_id": user_input.context.user_id if user_input.context else None,
            "integration": DOMAIN,
            "entity_id": self.entity_id,
        }

        # Add Home Assistant state information if available
        try:
            # Get basic HA information
            context_info["ha_version"] = self.hass.config.version
            context_info["ha_timezone"] = str(self.hass.config.time_zone)
            
            # Add some basic entity counts for context
            context_info["entity_count"] = len(self.hass.states.async_entity_ids())
            
        except Exception as e:
            _LOGGER.debug("Error getting HA context: %s", e)

        return context_info

    def _create_success_response(self, response_text: str) -> Dict[str, Any]:
        """Create a successful conversation response.
        
        Args:
            response_text: The text response from the AI agent.
            
        Returns:
            Dictionary representing a successful conversation response.
        """
        return {
            "response_type": "plain",
            "response": {
                "plain": {
                    "speech": response_text
                }
            }
        }

    def _create_error_response(
        self, 
        error_message: str, 
        error_type: str = "general_error"
    ) -> Dict[str, Any]:
        """Create an error conversation response.
        
        Args:
            error_message: The error message to return.
            error_type: The type of error that occurred.
            
        Returns:
            Dictionary representing an error conversation response.
        """
        return {
            "response_type": "error",
            "response": {
                "error": {
                    "type": error_type,
                    "message": error_message
                }
            }
        }

    async def async_reload(self, language: str | None = None) -> None:
        """Reload the conversation entity.
        
        This method is called when the conversation entity should be reloaded,
        for example when the language changes or configuration is updated.
        """
        _LOGGER.debug("Reloading GLM Agent conversation entity (language: %s)", language)
        
        # Reinitialize the agent
        self._initialize_agent()
        
        if self._agent:
            _LOGGER.info("GLM Agent conversation entity reloaded successfully")
        else:
            _LOGGER.error("Failed to reload GLM Agent conversation entity")

    async def async_prepare(self, language: str | None = None) -> None:
        """Prepare the conversation entity for use.
        
        This method is called when the conversation entity should be prepared
        for use, for example when Home Assistant starts or when the language
        changes.
        """
        _LOGGER.debug("Preparing GLM Agent conversation entity (language: %s)", language)
        
        # Ensure the agent is initialized
        if not self._agent:
            self._initialize_agent()
        
        # Additional preparation can be done here if needed
        if self._agent:
            _LOGGER.debug("GLM Agent conversation entity prepared successfully")
        else:
            _LOGGER.warning("GLM Agent conversation entity preparation incomplete")

    def _validate_conversation_input(self, user_input: ConversationInput) -> Dict[str, Any]:
        """Validate conversation input parameters.

        Args:
            user_input: The conversation input to validate.

        Returns:
            Dictionary with validation result and error message if invalid.
        """
        try:
            # Check if user_input is not None
            if user_input is None:
                return {"valid": False, "error": "No input provided"}

            # Check if user_input has required attributes
            if not hasattr(user_input, 'text'):
                return {"valid": False, "error": "Invalid input: missing text attribute"}

            if not hasattr(user_input, 'conversation_id'):
                return {"valid": False, "error": "Invalid input: missing conversation_id"}

            # Validate conversation_id
            if not user_input.conversation_id:
                return {"valid": False, "error": "Invalid input: empty conversation_id"}

            # Validate text type and content
            if not isinstance(user_input.text, str):
                return {"valid": False, "error": "Invalid input: text must be a string"}

            # Check text length (reasonable limits)
            if len(user_input.text) > 10000:  # 10K character limit
                return {"valid": False, "error": "Input too long (max 10,000 characters)"}

            # Check for potentially harmful content patterns
            import re
            dangerous_patterns = [
                r'<script[^>]*>.*?</script>',  # Script tags
                r'javascript:',                # JavaScript URLs
                r'data:text/html',           # Data URLs with HTML
            ]

            for pattern in dangerous_patterns:
                if re.search(pattern, user_input.text, re.IGNORECASE | re.DOTALL):
                    return {"valid": False, "error": "Input contains potentially unsafe content"}

            # Validate language if provided
            if hasattr(user_input, 'language') and user_input.language:
                if not isinstance(user_input.language, str):
                    return {"valid": False, "error": "Invalid input: language must be a string"}

                # Check if language is in supported list
                supported_languages = self.supported_languages
                if (supported_languages != "*" and
                    user_input.language not in supported_languages):
                    return {"valid": False, "error": f"Unsupported language: {user_input.language}"}

            # Validate context if provided
            if hasattr(user_input, 'context') and user_input.context:
                if not hasattr(user_input.context, 'user_id'):
                    return {"valid": False, "error": "Invalid input: context missing user_id"}

            return {"valid": True}

        except Exception as e:
            _LOGGER.error("Error validating conversation input: %s", e)
            return {"valid": False, "error": f"Validation error: {str(e)}"}

    @property
    def attribution(self) -> Optional[Dict[str, str]]:
        """Return attribution information for this conversation agent.

        Returns:
            Dictionary containing attribution information or None.
        """
        return {
            "name": "GLM Agent",
            "url": "https://github.com/ZhipuAI/glm-agent-ha"
        }

    async def _broadcast_conversation_update(
        self,
        message: str,
        response: str,
        conversation_id: str
    ) -> None:
        """Broadcast conversation update via secure WebSocket.

        Args:
            message: User message
            response: AI response
            conversation_id: Conversation ID
        """
        try:
            if hasattr(self._agent, 'websocket_manager'):
                # Create a temporary state-like object for broadcasting
                import datetime
                from homeassistant.helpers.typing import StateType

                conversation_data = {
                    "entity_id": self.entity_id,
                    "attributes": {
                        "conversation_id": conversation_id,
                        "last_message": message,
                        "last_response": response,
                        "timestamp": datetime.datetime.now().isoformat(),
                        "message_count": getattr(self, '_message_count', 0) + 1
                    },
                    "state": "conversing"
                }

                # Update message count
                self._message_count = getattr(self, '_message_count', 0) + 1

                # Broadcast via WebSocket manager
                await self._agent.websocket_manager.broadcast_entity_update(
                    self.entity_id,
                    None,
                    conversation_data
                )

                _LOGGER.debug("Conversation update broadcasted via WebSocket: %s", conversation_id)

        except Exception as e:
            _LOGGER.error("Error broadcasting conversation update: %s", e)
    async def async_added_to_hass(self) -> None:
        """When entity is added to Home Assistant."""
        await super().async_added_to_hass()
        # Platform-based conversation entities are automatically registered
        # No manual registration needed
        _LOGGER.info("GLM Agent conversation entity added to Home Assistant")

    async def async_will_remove_from_hass(self) -> None:
        """When entity will be removed from Home Assistant."""
        # Platform-based conversation entities are automatically unregistered
        await super().async_will_remove_from_hass()
        _LOGGER.info("GLM Agent conversation entity removed from Home Assistant")
