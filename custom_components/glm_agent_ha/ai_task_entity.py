"""AI Task entity for GLM Agent HA integration."""

from __future__ import annotations

import hashlib
import logging
import os
from datetime import datetime
from typing import Any

from homeassistant.components.ai_task import (
    AITaskEntity,
    AITaskEntityFeature,
    GenDataTask,
    GenDataTaskResult,
)
from homeassistant.components.media_source import async_resolve_media
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LLM_HASS_API
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.typing import ConfigType

from .agent import AiAgentHaAgent
from .const import (
    CONF_AI_PROVIDER,
    CONF_ENABLE_MCP_INTEGRATION,
    CONF_HA_BASE_URL,
    CONF_PLAN,
    DOMAIN,
    PLAN_PRO,
    PLAN_MAX,
)

_LOGGER = logging.getLogger(__name__)


class GLMAgentAITaskEntity(AITaskEntity):
    """AI Task entity for GLM Agent HA."""

    _attr_has_entity_name = True
    _attr_name = "GLM Agent AI Task"
    _attr_supported_features = AITaskEntityFeature.GENERATE_DATA

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the AI Task entity."""
        super().__init__(hass)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_ai_task"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="GLM Agent HA",
            manufacturer="GLM Agent HA",
            model=entry.data.get(CONF_PLAN, "lite"),
        )
        
        # Initialize agent
        self._agent = AiAgentHaAgent(hass, entry.data)
        self._mcp_manager = None
        
        # Check if MCP integration is available and enabled
        if (entry.options.get(CONF_ENABLE_MCP_INTEGRATION, True) and
            entry.data.get(CONF_PLAN) in [PLAN_PRO, PLAN_MAX]):
            # Get MCP manager from agent after it's initialized
            self._mcp_manager = getattr(self._agent, '_mcp_manager', None)
            if self._mcp_manager:
                _LOGGER.info("MCP integration available for AI Task entity")
            else:
                _LOGGER.debug("MCP manager not available in agent")
        else:
            _LOGGER.debug("MCP integration disabled or plan not supported")

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return True

    async def _async_generate_data(
        self, task: GenDataTask, chat_log: Any
    ) -> GenDataTaskResult:
        """Handle a generate data task."""
        _LOGGER.debug("Processing AI Task: %s", task.task_name)
        
        try:
            # Step 1: Process attachments using MCP (if Pro/Max plan)
            attachment_analyses = []
            if task.attachments and self._has_mcp_support():
                _LOGGER.debug("Processing %d attachments with MCP", len(task.attachments))
                for attachment in task.attachments:
                    try:
                        # Download media and save to www folder for MCP access
                        public_url = await self._download_and_save_media(
                            attachment.media_content_id
                        )
                        
                        # Analyze using Z.AI MCP with public URL
                        analysis = await self._analyze_media_with_mcp(public_url)
                        attachment_analyses.append(analysis)
                        _LOGGER.debug("Successfully analyzed attachment: %s", attachment.media_content_id)
                    except Exception as e:
                        _LOGGER.warning(
                            "Failed to analyze attachment %s: %s", 
                            attachment.media_content_id, e
                        )
                        # Continue without this attachment analysis
                        attachment_analyses.append(
                            f"Unable to analyze media {attachment.media_content_id}: {str(e)}"
                        )
            
            # Step 2: Combine instructions + attachment analyses
            enhanced_instructions = task.instructions
            if attachment_analyses:
                enhanced_instructions = f"""
{task.instructions}

Context from attached media:
{chr(10).join(f"- {analysis}" for analysis in attachment_analyses)}
""".strip()
            
            # Step 3: Generate structured data using GLM + structured output
            result = await self._agent.process_query(
                prompt=enhanced_instructions,
                structure=task.structure,
                chat_log=chat_log
            )
            
            return GenDataTaskResult(
                conversation_id=chat_log.conversation_id,
                data=result
            )
            
        except Exception as e:
            _LOGGER.error("Error processing AI Task %s: %s", task.task_name, e)
            raise

    def _has_mcp_support(self) -> bool:
        """Check if MCP integration is available and enabled."""
        return (self._mcp_manager is not None and 
                self._entry.options.get(CONF_ENABLE_MCP_INTEGRATION, True))

    async def _download_and_save_media(self, media_content_id: str) -> str:
        """Download media and save to www folder, return public URL."""
        _LOGGER.debug("Downloading media: %s", media_content_id)
        
        # Resolve media source
        media = await async_resolve_media(self.hass, media_content_id, None)
        _LOGGER.debug("Resolved media URL: %s", media.url)
        
        # Download media content
        async with self.hass.helpers.aiohttp_client.async_get_clientsession().get(
            media.url
        ) as response:
            if response.status != 200:
                raise ValueError(f"Failed to download media: HTTP {response.status}")
            media_bytes = await response.read()
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        content_hash = hashlib.md5(media_bytes).hexdigest()[:8]
        extension = media_content_id.split('.')[-1] or 'jpg'
        filename = f"ai_task_{timestamp}_{content_hash}.{extension}"
        
        # Save to HA's www folder
        www_path = os.path.join(self.hass.config.path("www"), filename)
        
        # Ensure www directory exists
        os.makedirs(os.path.dirname(www_path), exist_ok=True)
        
        with open(www_path, 'wb') as f:
            f.write(media_bytes)
        
        _LOGGER.debug("Saved media to: %s", www_path)
        
        # Return public URL (configurable base URL)
        base_url = self._entry.options.get(
            CONF_HA_BASE_URL, 
            f"http://{self.hass.config.location_name}.local:8123"
        )
        public_url = f"{base_url}/local/{filename}"
        
        _LOGGER.debug("Generated public URL: %s", public_url)
        return public_url

    async def _analyze_media_with_mcp(self, public_url: str) -> str:
        """Analyze media using MCP with public URL."""
        _LOGGER.debug("Analyzing media via MCP: %s", public_url)
        
        try:
            # Use the Z.AI MCP manager to analyze the image
            analysis = await self._mcp_manager.analyze_image(
                public_url,  # Use URL instead of bytes
                prompt="Describe this image in detail for AI analysis"
            )
            _LOGGER.debug("MCP analysis completed successfully")
            return analysis
        except Exception as e:
            _LOGGER.error("MCP analysis failed: %s", e)
            raise