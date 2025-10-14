"""Voice Pipeline Integration for GLM Agent HA."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .agent import AiAgentHaAgent
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class GLMVoicePipeline:
    """GLM Agent Voice Pipeline integration."""

    def __init__(self, hass: HomeAssistant, config: ConfigType) -> None:
        """Initialize the voice pipeline."""
        self.hass = hass
        self.config = config
        self.agent: Optional[AiAgentHaAgent] = None
        self._initialize_agent()

    def _initialize_agent(self) -> None:
        """Initialize the AI agent."""
        try:
            self.agent = AiAgentHaAgent(self.hass, self.config)
            _LOGGER.info("GLM Voice Pipeline initialized")
        except Exception as e:
            _LOGGER.error("Failed to initialize GLM Voice Pipeline: %s", e)

    async def process_voice_command(
        self,
        text: str,
        language: str = "en",
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        device_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Process a voice command."""
        if not self.agent:
            return {
                "error": "GLM Agent not initialized",
                "error_type": "agent_not_initialized",
                "success": False
            }

        try:
            # Get voice context information
            voice_context = await self._get_voice_context(
                text, language, conversation_id, user_id, device_id, context
            )

            # Process the voice command with GLM agent
            result = await self.agent.process_query(
                prompt=text,
                context={
                    **voice_context,
                    "request_source": "voice_pipeline",
                    "language": language,
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                    "device_id": device_id,
                }
            )

            if result and result.get("success"):
                return {
                    "response": result.get("answer", "I'm sorry, I couldn't process your voice command."),
                    "success": True,
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                    "device_id": device_id,
                    "language": language,
                    "actions": result.get("actions", []),
                }
            else:
                error_msg = result.get("error", "I'm sorry, I couldn't process your voice command.")
                return {
                    "response": error_msg,
                    "success": False,
                    "error": error_msg,
                    "error_type": "processing_error",
                    "conversation_id": conversation_id,
                }

        except Exception as e:
            _LOGGER.error("Error processing voice command: %s", e)
            return {
                "response": f"I'm sorry, an error occurred: {str(e)}",
                "success": False,
                "error": str(e),
                "error_type": "unexpected_error",
                "conversation_id": conversation_id,
            }

    async def _get_voice_context(
        self,
        text: str,
        language: str,
        conversation_id: Optional[str],
        user_id: Optional[str],
        device_id: Optional[str],
        context: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Get context information for voice command."""
        voice_context = {
            "request_source": "voice_pipeline",
            "language": language,
            "conversation_id": conversation_id,
            "user_id": user_id,
            "device_id": device_id,
        }

        # Add device information if available
        if device_id:
            voice_context["device_info"] = await self._get_device_info(device_id)

        # Add user information if available
        if user_id:
            voice_context["user_info"] = await self._get_user_info(user_id)

        # Add current state information for voice-relevant entities
        voice_context["current_states"] = await self._get_voice_relevant_states()

        # Add any additional context
        if context:
            voice_context.update(context)

        return voice_context

    async def _get_device_info(self, device_id: str) -> Dict[str, Any]:
        """Get device information."""
        try:
            # Try to get device registry information
            device_registry = self.hass.data.get("device_registry")
            if device_registry:
                device = device_registry.async_get(device_id)
                if device:
                    return {
                        "name": device.name,
                        "model": device.model,
                        "manufacturer": device.manufacturer,
                        "area_id": device.area_id,
                    }
        except Exception as e:
            _LOGGER.debug("Error getting device info: %s", e)

        return {"device_id": device_id}

    async def _get_user_info(self, user_id: str) -> Dict[str, Any]:
        """Get user information."""
        try:
            # Try to get user information
            user = self.hass.users.async_get(user_id)
            if user:
                return {
                    "name": user.name,
                    "is_admin": user.is_admin,
                    "is_owner": user.is_owner,
                    "system_generated": user.system_generated,
                }
        except Exception as e:
            _LOGGER.debug("Error getting user info: %s", e)

        return {"user_id": user_id}

    async def _get_voice_relevant_states(self) -> Dict[str, Any]:
        """Get states of entities commonly used in voice commands."""
        voice_relevant = {}

        try:
            # Get common voice-controlled entities
            entity_categories = [
                "light", "switch", "cover", "media_player", "climate",
                "lock", "camera", "sensor", "input_boolean", "input_select"
            ]

            states = self.hass.states
            for entity_id, state in states.items():
                domain = entity_id.split(".")[0]
                if domain in entity_categories:
                    voice_relevant[entity_id] = {
                        "state": state.state,
                        "attributes": state.attributes,
                        "friendly_name": state.attributes.get("friendly_name", entity_id),
                        "domain": domain,
                    }

        except Exception as e:
            _LOGGER.debug("Error getting voice relevant states: %s", e)

        return voice_relevant

    async def process_intent(
        self,
        intent: str,
        entities: Dict[str, Any],
        text: str,
        language: str = "en",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Process a voice intent."""
        if not self.agent:
            return {
                "error": "GLM Agent not initialized",
                "error_type": "agent_not_initialized",
                "success": False
            }

        try:
            # Construct intent-based prompt
            intent_prompt = self._construct_intent_prompt(intent, entities, text)

            # Process the intent with GLM agent
            result = await self.agent.process_query(
                prompt=intent_prompt,
                context={
                    "request_source": "voice_intent",
                    "intent": intent,
                    "entities": entities,
                    "original_text": text,
                    "language": language,
                    **kwargs
                }
            )

            if result and result.get("success"):
                return {
                    "response": result.get("answer", "I'm sorry, I couldn't process that intent."),
                    "success": True,
                    "intent": intent,
                    "entities": entities,
                    "actions": result.get("actions", []),
                }
            else:
                error_msg = result.get("error", "I'm sorry, I couldn't process that intent.")
                return {
                    "response": error_msg,
                    "success": False,
                    "error": error_msg,
                    "error_type": "processing_error",
                    "intent": intent,
                }

        except Exception as e:
            _LOGGER.error("Error processing voice intent: %s", e)
            return {
                "response": f"I'm sorry, an error occurred: {str(e)}",
                "success": False,
                "error": str(e),
                "error_type": "unexpected_error",
                "intent": intent,
            }

    def _construct_intent_prompt(
        self, intent: str, entities: Dict[str, Any], text: str
    ) -> str:
        """Construct a prompt from intent and entities."""
        prompt = f"Intent: {intent}\n"
        prompt += f"Original text: {text}\n"

        if entities:
            prompt += "Entities:\n"
            for entity_type, entity_value in entities.items():
                prompt += f"  {entity_type}: {entity_value}\n"

        prompt += "\nPlease process this intent and provide the appropriate response or action."

        return prompt


def create_voice_pipeline(hass: HomeAssistant, config: ConfigType) -> Optional[GLMVoicePipeline]:
    """Create GLM Agent Voice Pipeline."""
    try:
        return GLMVoicePipeline(hass, config)
    except Exception as e:
        _LOGGER.error("Error creating voice pipeline: %s", e)
        return None


# Helper function for voice pipeline integration
async def setup_voice_integration(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up voice integration."""
    try:
        pipeline = create_voice_pipeline(hass, config)
        if pipeline:
            # Store pipeline for later use
            if DOMAIN not in hass.data:
                hass.data[DOMAIN] = {}
            hass.data[DOMAIN]["voice_pipeline"] = pipeline
            _LOGGER.info("Voice integration set up successfully")
            return True
        else:
            _LOGGER.error("Failed to create voice pipeline")
            return False
    except Exception as e:
        _LOGGER.error("Error setting up voice integration: %s", e)
        return False