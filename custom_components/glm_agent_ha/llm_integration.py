"""LLM Pipeline Integration for GLM Agent HA."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from homeassistant.components import conversation
from homeassistant.components.conversation import AbstractConversationAgent
from homeassistant.components.conversation.const import (
    ConversationAgent,
    ConversationResult,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import ulid

from .agent import AiAgentHaAgent
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class GLMConversationAgent(AbstractConversationAgent):
    """GLM Conversation Agent for Home Assistant LLM Pipeline."""

    def __init__(self, hass: HomeAssistant, config: ConfigType, entry_id: str) -> None:
        """Initialize the conversation agent."""
        super().__init__(hass, config)
        self.entry_id = entry_id
        self.config = config
        self.agent: Optional[AiAgentHaAgent] = None
        self._initialize_agent()

    def _initialize_agent(self) -> None:
        """Initialize the AI agent."""
        try:
            self.agent = AiAgentHaAgent(self.hass, self.config)
            _LOGGER.info("GLM Conversation Agent initialized for entry: %s", self.entry_id)
        except Exception as e:
            _LOGGER.error("Failed to initialize GLM Conversation Agent: %s", e)

    @property
    def supported_languages(self) -> List[str]:
        """Return supported languages."""
        return ["en", "en-US"]

    async def async_process(
        self,
        user_input: conversation.ConversationInput,
    ) -> ConversationResult:
        """Process a conversation input."""
        if not self.agent:
            return conversation.ConversationResult(
                response=conversation.ConversationResponse(
                    response_type=conversation.ConversationResponseType.ERROR,
                    response={
                        "error_type": "agent_not_initialized",
                        "error_message": "GLM Agent is not properly initialized",
                    },
                ),
            )

        try:
            # Get context information from Home Assistant
            context = await self._get_assistant_context(user_input)

            # Process the query with GLM agent
            result = await self.agent.process_query(
                prompt=user_input.text,
                context=context,
                conversation_id=user_input.conversation_id,
                user_id=user_input.user_id,
            )

            if result and result.get("success"):
                return conversation.ConversationResult(
                    response=conversation.ConversationResponse(
                        response_type=conversation.ConversationResponseType.PLAIN,
                        response={"plain": {"speech": result.get("answer", "I'm sorry, I couldn't process your request.")}},
                    ),
                )
            else:
                error_msg = result.get("error", "I'm sorry, I couldn't process your request.")
                return conversation.ConversationResult(
                    response=conversation.ConversationResponse(
                        response_type=conversation.ConversationResponseType.ERROR,
                        response={
                            "error_type": "processing_error",
                            "error_message": error_msg,
                        },
                    ),
                )

        except Exception as e:
            _LOGGER.error("Error processing conversation: %s", e)
            return conversation.ConversationResult(
                response=conversation.ConversationResponse(
                    response_type=conversation.ConversationResponseType.ERROR,
                    response={
                        "error_type": "unexpected_error",
                        "error_message": f"An unexpected error occurred: {str(e)}",
                    },
                ),
            )

    async def _get_assistant_context(
        self, user_input: conversation.ConversationInput
    ) -> Dict[str, Any]:
        """Get context information for the assistant."""
        context = {
            "request_source": "assist_pipeline",
            "conversation_id": user_input.conversation_id,
            "user_id": user_input.user_id,
            "language": user_input.language,
        }

        # Add device information if available
        if user_input.device_id:
            context["device_id"] = user_input.device_id

        # Add exposed entities if available
        if user_input.exposed_entities:
            context["exposed_entities"] = list(user_input.exposed_entities)

        # Add current state information for common entities
        try:
            states = {}
            if user_input.exposed_entities:
                for entity_id in user_input.exposed_entities:
                    state = self.hass.states.get(entity_id)
                    if state:
                        states[entity_id] = {
                            "state": state.state,
                            "attributes": state.attributes,
                            "friendly_name": state.attributes.get("friendly_name", entity_id),
                            "domain": entity_id.split(".")[0],
                        }

            context["current_states"] = states
        except Exception as e:
            _LOGGER.debug("Error getting current states: %s", e)

        return context

    async def async_reload(self, config: ConfigType) -> None:
        """Reload the conversation agent."""
        self.config = config
        self._initialize_agent()
        _LOGGER.info("GLM Conversation Agent reloaded")


def get_conversation_agent(
    hass: HomeAssistant,
    config: ConfigType,
    entry_id: str,
) -> ConversationAgent:
    """Return a conversation agent."""
    return GLMConversationAgent(hass, config, entry_id)


# Conversation handler registration
async def async_setup_conversation(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up conversation platform."""
    # This will be called by Home Assistant to set up the conversation agent
    return True


# LLM API handler
async def async_get_api_response(
    hass: HomeAssistant,
    conversation_id: str,
    text: str,
    language: str,
    context: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> Any:
    """Get API response for LLM integration."""
    try:
        # Get the active GLM Agent HA config entry
        from homeassistant.config_entries import ConfigEntry
        from .const import DOMAIN

        entries = hass.config_entries.async_entries(DOMAIN)
        if not entries:
            _LOGGER.error("No GLM Agent HA config entry found")
            return {
                "error": "No GLM Agent HA configuration found",
                "error_type": "no_config",
            }

        config_entry = entries[0]
        config_data = dict(config_entry.data)

        # Create agent instance
        agent = AiAgentHaAgent(hass, config_data)

        # Process the query
        result = await agent.process_query(
            prompt=text,
            context={
                **(context or {}),
                "request_source": "llm_api",
                "conversation_id": conversation_id,
                "language": language,
            }
        )

        if result and result.get("success"):
            return {
                "response": result.get("answer", ""),
                "success": True,
                "usage": result.get("usage", {}),
            }
        else:
            return {
                "error": result.get("error", "Failed to process request"),
                "error_type": "processing_error",
                "success": False,
            }

    except Exception as e:
        _LOGGER.error("Error in LLM API response: %s", e)
        return {
            "error": str(e),
            "error_type": "unexpected_error",
            "success": False,
        }