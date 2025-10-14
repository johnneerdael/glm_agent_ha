"""AI Task Pipeline Integration for GLM Agent HA."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

try:
    from homeassistant.components.ai_task import (
        AITaskEntity,
        AITaskEntityFeature,
        GenDataTask,
        GenDataTaskResult,
    )
    AI_TASK_AVAILABLE = True
except ImportError:
    AI_TASK_AVAILABLE = False
    # Create placeholder classes for compatibility
    class AITaskEntity:
        def __init__(self, hass):
            pass

    class AITaskEntityFeature:
        GENERATE_DATA = 1

    class GenDataTask:
        def __init__(self, *args, **kwargs):
            pass

    class GenDataTaskResult:
        def __init__(self, *args, **kwargs):
            pass

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .agent import AiAgentHaAgent
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class GLMAgentAITaskPipeline:
    """GLM Agent AI Task Pipeline integration."""

    def __init__(self, hass: HomeAssistant, config: ConfigType) -> None:
        """Initialize the AI Task pipeline."""
        self.hass = hass
        self.config = config
        self.agent: Optional[AiAgentHaAgent] = None
        self._initialize_agent()

    def _initialize_agent(self) -> None:
        """Initialize the AI agent."""
        try:
            self.agent = AiAgentHaAgent(self.hass, self.config)
            _LOGGER.info("GLM AI Task Pipeline initialized")
        except Exception as e:
            _LOGGER.error("Failed to initialize GLM AI Task Pipeline: %s", e)

    async def process_ai_task(
        self,
        task: GenDataTask,
        chat_log: Any,
    ) -> GenDataTaskResult:
        """Process an AI Task."""
        if not self.agent:
            return GenDataTaskResult(
                conversation_id=chat_log.conversation_id,
                data={
                    "error": "GLM Agent not initialized",
                    "error_type": "agent_not_initialized"
                }
            )

        try:
            # Validate task parameters
            validation_result = self._validate_task_parameters(task)
            if not validation_result["valid"]:
                _LOGGER.error("Invalid AI Task parameters: %s", validation_result["error"])
                return GenDataTaskResult(
                    conversation_id=chat_log.conversation_id,
                    data={
                        "error": validation_result["error"],
                        "error_type": "invalid_parameters"
                    }
                )

            # Process attachments if present
            attachment_context = []
            if task.attachments:
                attachment_context = await self._process_attachments(task.attachments)

            # Prepare enhanced prompt with context
            enhanced_prompt = self._prepare_enhanced_prompt(task, attachment_context)

            # Process with GLM agent
            result = await self.agent.process_query(
                prompt=enhanced_prompt,
                structure=task.structure,
                context={
                    "request_source": "ai_task_pipeline",
                    "task_name": task.task_name,
                    "conversation_id": chat_log.conversation_id,
                    "attachment_context": attachment_context,
                }
            )

            # Validate and return result
            if result and result.get("success"):
                data = result.get("data", result.get("answer", ""))
                return GenDataTaskResult(
                    conversation_id=chat_log.conversation_id,
                    data=data
                )
            else:
                error_msg = result.get("error", "Failed to process AI Task")
                return GenDataTaskResult(
                    conversation_id=chat_log.conversation_id,
                    data={
                        "error": error_msg,
                        "error_type": "processing_error",
                        "attachment_context": attachment_context
                    }
                )

        except Exception as e:
            _LOGGER.error("Error processing AI Task: %s", e)
            return GenDataTaskResult(
                conversation_id=chat_log.conversation_id,
                data={
                    "error": f"Unexpected error: {str(e)}",
                    "error_type": "unexpected_error"
                }
            )

    def _validate_task_parameters(self, task: GenDataTask) -> Dict[str, Any]:
        """Validate AI Task parameters."""
        try:
            if not task.task_name or not isinstance(task.task_name, str):
                return {"valid": False, "error": "Invalid or missing task name"}

            if not task.instructions or not isinstance(task.instructions, str):
                return {"valid": False, "error": "Invalid or missing instructions"}

            if len(task.instructions) > 10000:
                return {"valid": False, "error": "Instructions too long (max 10,000 characters)"}

            if task.attachments and len(task.attachments) > 10:
                return {"valid": False, "error": "Too many attachments (max 10)"}

            return {"valid": True}

        except Exception as e:
            return {"valid": False, "error": f"Validation error: {str(e)}"}

    async def _process_attachments(self, attachments: List[Any]) -> List[str]:
        """Process attachments for AI Task."""
        attachment_context = []

        for i, attachment in enumerate(attachments):
            try:
                if hasattr(attachment, 'media_content_id'):
                    # For Home Assistant media attachments
                    analysis = await self._analyze_home_assistant_media(attachment)
                    if analysis:
                        attachment_context.append(analysis)
                elif hasattr(attachment, 'url'):
                    # For URL-based attachments
                    analysis = await self._analyze_media_url(attachment.url)
                    if analysis:
                        attachment_context.append(analysis)
                else:
                    _LOGGER.warning("Unsupported attachment format at index %d", i)
            except Exception as e:
                _LOGGER.error("Error processing attachment %d: %s", i, e)
                attachment_context.append(f"Error processing attachment {i+1}: {str(e)}")

        return attachment_context

    async def _analyze_home_assistant_media(self, attachment: Any) -> Optional[str]:
        """Analyze Home Assistant media attachment."""
        try:
            if not self.agent or not hasattr(self.agent, 'mcp_manager'):
                return f"Media attachment: {getattr(attachment, 'media_content_id', 'unknown')} (MCP analysis not available)"

            # Try to get a public URL for the media
            public_url = await self._get_media_url(attachment.media_content_id)
            if public_url:
                return await self.agent.mcp_manager.analyze_image(
                    public_url,
                    prompt="Analyze this media for AI task processing"
                )
            else:
                return f"Media attachment: {attachment.media_content_id} (URL not available)"

        except Exception as e:
            _LOGGER.error("Error analyzing Home Assistant media: %s", e)
            return f"Error analyzing media: {str(e)}"

    async def _analyze_media_url(self, url: str) -> Optional[str]:
        """Analyze media from URL."""
        try:
            if not self.agent or not hasattr(self.agent, 'mcp_manager'):
                return f"Media URL analysis not available (MCP not initialized)"

            return await self.agent.mcp_manager.analyze_image(
                url,
                prompt="Analyze this media for AI task processing"
            )

        except Exception as e:
            _LOGGER.error("Error analyzing media URL: %s", e)
            return f"Error analyzing media URL: {str(e)}"

    async def _get_media_url(self, media_content_id: str) -> Optional[str]:
        """Get public URL for Home Assistant media."""
        try:
            from homeassistant.components.media_source import async_resolve_media

            media = await async_resolve_media(self.hass, media_content_id, None)
            if media and hasattr(media, 'url'):
                return str(media.url)
        except Exception as e:
            _LOGGER.debug("Error resolving media URL: %s", e)

        return None

    def _prepare_enhanced_prompt(
        self, task: GenDataTask, attachment_context: List[str]
    ) -> str:
        """Prepare enhanced prompt with attachment context."""
        base_prompt = task.instructions

        if not attachment_context:
            return base_prompt

        # Add attachment context
        context_section = "\n\nAttachment Analysis:\n"
        for i, analysis in enumerate(attachment_context, 1):
            context_section += f"{i}. {analysis}\n"

        return f"{base_prompt}{context_section}"


def create_ai_task_pipeline(hass: HomeAssistant, config: ConfigType) -> Optional[GLMAgentAITaskPipeline]:
    """Create GLM Agent AI Task Pipeline."""
    if not AI_TASK_AVAILABLE:
        _LOGGER.warning("AI Task components not available")
        return None

    try:
        return GLMAgentAITaskPipeline(hass, config)
    except Exception as e:
        _LOGGER.error("Error creating AI Task Pipeline: %s", e)
        return None


# Helper function for AI Task integration
async def setup_ai_task_integration(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up AI Task integration if available."""
    if not AI_TASK_AVAILABLE:
        _LOGGER.debug("AI Task integration not available - skipping")
        return True

    try:
        pipeline = create_ai_task_pipeline(hass, config)
        if pipeline:
            # Store pipeline for later use
            if DOMAIN not in hass.data:
                hass.data[DOMAIN] = {}
            hass.data[DOMAIN]["ai_task_pipeline"] = pipeline
            _LOGGER.info("AI Task integration set up successfully")
            return True
        else:
            _LOGGER.error("Failed to create AI Task pipeline")
            return False
    except Exception as e:
        _LOGGER.error("Error setting up AI Task integration: %s", e)
        return False