"""AI Task entity for GLM Agent HA integration."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import re
import secrets
import time
import urllib.parse
from datetime import datetime
from typing import Any

try:
    import aiohttp
except ImportError:
    aiohttp = None

try:
    from homeassistant.components.ai_task import (
        AITaskEntity,
        AITaskEntityFeature,
        GenDataTask,
        GenDataTaskResult,
    )
    AI_TASK_COMPONENTS_AVAILABLE = True
except (ImportError, ModuleNotFoundError) as e:
    AI_TASK_COMPONENTS_AVAILABLE = False
    # Create placeholder classes to avoid import errors
    class AITaskEntity:
        def __init__(self):
            pass

    class AITaskEntityFeature:
        GENERATE_DATA = 1

    class GenDataTask:
        def __init__(self, *args, **kwargs):
            pass

    class GenDataTaskResult:
        def __init__(self, *args, **kwargs):
            pass
from homeassistant.components.media_source import async_resolve_media
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LLM_HASS_API
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
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

# Security constants for media processing
MAX_FILE_SIZE_MB = 50  # Maximum file size in MB
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
ALLOWED_EXTENSIONS = {
    'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp',  # Images
    'mp4', 'avi', 'mov', 'mkv', 'webm',  # Videos
    'mp3', 'wav', 'ogg', 'flac', 'm4a'  # Audio
}
ALLOWED_MIME_TYPES = {
    'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp',
    'video/mp4', 'video/avi', 'video/quicktime', 'video/x-matroska', 'video/webm',
    'audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/flac', 'audio/mp4'
}
SECURE_FILENAME_LENGTH = 16
MAX_FILE_AGE_HOURS = 24  # Clean up files older than 24 hours
URL_REGEX = re.compile(
    r'^https?://'  # http:// or https://
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
    r'localhost|'  # localhost...
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
    r'(?::\d+)?'  # optional port
    r'(?:/?|[/?]\S+)$', re.IGNORECASE)

def _is_safe_url(url: str) -> bool:
    """Validate if URL is safe for downloading."""
    if not url or not isinstance(url, str):
        return False

    # Check against regex
    if not URL_REGEX.match(url):
        return False

    # Parse URL and check components
    try:
        parsed = urllib.parse.urlparse(url)

        # Reject file:// URLs
        if parsed.scheme in ('file', 'ftp'):
            return False

        # Reject localhost/private IPs in production
        hostname = parsed.hostname
        if hostname:
            # Basic check for private IP ranges
            if (hostname.startswith('127.') or
                hostname.startswith('10.') or
                hostname.startswith('192.168.') or
                hostname.startswith('172.')):
                _LOGGER.warning("Blocking download from private IP: %s", hostname)
                return False

        return True
    except Exception:
        return False

def _is_allowed_extension(filename: str) -> bool:
    """Check if file extension is allowed."""
    if not filename:
        return False

    # Get extension without the dot
    extension = filename.split('.')[-1].lower()
    return extension in ALLOWED_EXTENSIONS

def _generate_secure_filename(original_filename: str) -> str:
    """Generate a secure, unpredictable filename."""
    # Get original extension
    extension = ''
    if original_filename and '.' in original_filename:
        extension = original_filename.split('.')[-1].lower()
        if extension not in ALLOWED_EXTENSIONS:
            extension = 'jpg'  # Default fallback

    # Generate random identifier
    random_part = secrets.token_urlsafe(SECURE_FILENAME_LENGTH)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    return f"ai_task_{timestamp}_{random_part}.{extension}"

async def _cleanup_old_files(ai_task_dir: str) -> None:
    """Clean up files older than MAX_FILE_AGE_HOURS."""
    try:
        import time
        current_time = time.time()
        max_age_seconds = MAX_FILE_AGE_HOURS * 3600

        if not os.path.exists(ai_task_dir):
            return

        cleaned_count = 0
        for filename in os.listdir(ai_task_dir):
            file_path = os.path.join(ai_task_dir, filename)

            # Only clean up ai_task files
            if not filename.startswith('ai_task_'):
                continue

            try:
                file_stat = os.stat(file_path)
                file_age = current_time - file_stat.st_mtime

                if file_age > max_age_seconds:
                    os.remove(file_path)
                    cleaned_count += 1
                    _LOGGER.debug("Cleaned up old file: %s", filename)

            except OSError as e:
                _LOGGER.warning("Failed to clean up file %s: %s", filename, e)

        if cleaned_count > 0:
            _LOGGER.info("Cleaned up %d old media files", cleaned_count)

    except Exception as e:
        _LOGGER.warning("Error during file cleanup: %s", e)


class GLMAgentAITaskEntity(AITaskEntity):
    """AI Task entity for GLM Agent HA."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the AI Task entity."""
        if not AI_TASK_COMPONENTS_AVAILABLE:
            _LOGGER.warning("AI Task components not available, entity will be disabled")
            self._attr_available = False
            return

        # Don't call super().__init__(hass) - AITaskEntity doesn't take hass parameter
        # Just set the required attributes directly
        self._hass = hass
        self._entry = entry
        self._attr_has_entity_name = True
        self._attr_name = "AI Task"
        self._attr_supported_features = AITaskEntityFeature.GENERATE_DATA
        self._attr_unique_id = f"{entry.entry_id}_ai_task"

        # Create proper device info for GLM Agent HA
        plan_type = entry.data.get(CONF_PLAN, "lite").title()
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="GLM Agent HA",
            manufacturer="Zhipu AI",
            model=f"GLM Agent {plan_type}",
            entry_type=dr.DeviceEntryType.SERVICE,
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
        if not AI_TASK_COMPONENTS_AVAILABLE:
            return False
        return True

    async def _async_generate_data(
        self, task: GenDataTask, chat_log: Any
    ) -> GenDataTaskResult:
        """Handle a generate data task with enhanced stability and error handling."""
        _LOGGER.debug("Processing AI Task: %s with %d attachments",
                      task.task_name, len(task.attachments or []))

        start_time = time.time()

        try:
            # Step 1: Validate task parameters
            validation_result = self._validate_task_parameters(task)
            if not validation_result["valid"]:
                error_msg = f"Invalid task parameters: {validation_result['error']}"
                _LOGGER.error(error_msg)
                raise ValueError(error_msg)

            # Step 2: Process attachments with enhanced error handling
            attachment_analyses = []
            successful_attachments = 0
            failed_attachments = 0

            if task.attachments and self._has_mcp_support():
                _LOGGER.debug("Processing %d attachments with MCP", len(task.attachments))

                # Limit the number of attachments to prevent resource exhaustion
                max_attachments = 5  # Reasonable limit
                attachments_to_process = task.attachments[:max_attachments]

                if len(task.attachments) > max_attachments:
                    _LOGGER.warning("Limiting attachments to %d (had %d)",
                                  max_attachments, len(task.attachments))

                for i, attachment in enumerate(attachments_to_process):
                    try:
                        # Add timeout to prevent hanging
                        public_url = await asyncio.wait_for(
                            self._download_and_save_media(attachment.media_content_id),
                            timeout=120.0  # 2 minutes max per attachment
                        )

                        # Add timeout to MCP analysis
                        analysis = await asyncio.wait_for(
                            self._analyze_media_with_mcp(public_url),
                            timeout=180.0  # 3 minutes max per analysis
                        )

                        attachment_analyses.append(analysis)
                        successful_attachments += 1
                        _LOGGER.debug("Successfully analyzed attachment %d/%d: %s",
                                      i + 1, len(attachments_to_process), attachment.media_content_id)

                    except asyncio.TimeoutError:
                        failed_attachments += 1
                        error_msg = f"Timeout processing attachment {attachment.media_content_id}"
                        _LOGGER.warning(error_msg)
                        attachment_analyses.append(error_msg)

                    except Exception as e:
                        failed_attachments += 1
                        error_msg = f"Failed to analyze attachment {attachment.media_content_id}: {str(e)}"
                        _LOGGER.warning(error_msg)
                        attachment_analyses.append(error_msg)

                # Log attachment processing summary
                _LOGGER.info("Attachment processing complete: %d successful, %d failed",
                            successful_attachments, failed_attachments)

            # Step 3: Prepare enhanced instructions with attachment context
            enhanced_instructions = self._prepare_enhanced_instructions(
                task.instructions, attachment_analyses
            )

            # Step 4: Generate structured data with timeout and retry logic
            try:
                result = await asyncio.wait_for(
                    self._agent.process_query(
                        prompt=enhanced_instructions,
                        structure=task.structure,
                        chat_log=chat_log
                    ),
                    timeout=300.0  # 5 minutes max for AI processing
                )

                # Validate the result structure
                if not self._validate_ai_result(result, task.structure):
                    _LOGGER.warning("AI result validation failed, using fallback")
                    result = self._create_fallback_result(task.structure, attachment_analyses)

            except asyncio.TimeoutError:
                _LOGGER.error("AI processing timeout for task: %s", task.task_name)
                result = self._create_fallback_result(task.structure, attachment_analyses)
                # Add timeout notice to result
                if isinstance(result, dict):
                    result["timeout_error"] = True
                    result["timeout_notice"] = "AI processing timed out, using fallback result"

            except Exception as e:
                _LOGGER.error("AI processing error for task %s: %s", task.task_name, e)
                result = self._create_fallback_result(task.structure, attachment_analyses)
                # Add error notice to result
                if isinstance(result, dict):
                    result["processing_error"] = True
                    result["error_notice"] = f"Processing error: {str(e)}"

            # Calculate processing time
            processing_time = time.time() - start_time
            _LOGGER.info("AI Task %s completed in %.2fs with %d/%d attachments processed",
                        task.task_name, processing_time, successful_attachments,
                        len(task.attachments or []))

            # Broadcast task completion via secure WebSocket
            await self._broadcast_task_update(task, result, processing_time, successful_attachments)

            return GenDataTaskResult(
                conversation_id=chat_log.conversation_id,
                data=result
            )

        except Exception as e:
            processing_time = time.time() - start_time
            _LOGGER.error("Critical error processing AI Task %s after %.2fs: %s",
                         task.task_name, processing_time, e)

            # Return a fallback result even on critical errors
            fallback_result = self._create_fallback_result(task.structure, [])
            if isinstance(fallback_result, dict):
                fallback_result["critical_error"] = True
                fallback_result["error_message"] = str(e)

            return GenDataTaskResult(
                conversation_id=chat_log.conversation_id,
                data=fallback_result
            )

    def _validate_task_parameters(self, task: GenDataTask) -> Dict[str, Any]:
        """Validate task parameters before processing."""
        try:
            # Check task name
            if not task.task_name or not isinstance(task.task_name, str):
                return {"valid": False, "error": "Invalid or missing task name"}

            # Check instructions
            if not task.instructions or not isinstance(task.instructions, str):
                return {"valid": False, "error": "Invalid or missing instructions"}

            # Check instructions length
            if len(task.instructions) > 10000:  # 10K character limit
                return {"valid": False, "error": "Instructions too long (max 10,000 characters)"}

            # Check attachments
            if task.attachments:
                if len(task.attachments) > 10:  # Reasonable limit
                    return {"valid": False, "error": "Too many attachments (max 10)"}

                for i, attachment in enumerate(task.attachments):
                    if not hasattr(attachment, 'media_content_id'):
                        return {"valid": False, "error": f"Attachment {i+1} missing media_content_id"}

                    if not attachment.media_content_id:
                        return {"valid": False, "error": f"Attachment {i+1} has empty media_content_id"}

            return {"valid": True}

        except Exception as e:
            return {"valid": False, "error": f"Validation error: {str(e)}"}

    def _prepare_enhanced_instructions(self, instructions: str, attachment_analyses: List[str]) -> str:
        """Prepare enhanced instructions with attachment context."""
        if not attachment_analyses:
            return instructions

        # Create attachment context section
        attachment_context = "Context from attached media:"
        for i, analysis in enumerate(attachment_analyses):
            attachment_context += f"\n{i+1}. {analysis}"

        # Combine with original instructions
        return f"""{instructions}

{attachment_context}""".strip()

    def _validate_ai_result(self, result: Any, expected_structure: Any) -> bool:
        """Validate that the AI result matches expected structure."""
        try:
            # Basic validation - ensure we got some result
            if result is None:
                return False

            # For structured results, try to validate structure
            if expected_structure and isinstance(result, dict):
                # Check if result has expected keys based on structure
                # This is a basic validation - could be enhanced
                return bool(result)

            return True

        except Exception as e:
            _LOGGER.warning("Result validation error: %s", e)
            return False

    def _create_fallback_result(self, structure: Any, attachment_analyses: List[str]) -> Any:
        """Create a fallback result when AI processing fails."""
        if attachment_analyses:
            # If we have attachment analyses, create result from them
            if structure and isinstance(structure, dict):
                fallback = structure.copy()
                # Try to populate with attachment analysis
                fallback["attachment_analyses"] = attachment_analyses
                fallback["processing_status"] = "fallback_with_attachments"
                return fallback
            else:
                return {"attachment_analyses": attachment_analyses, "processing_status": "fallback"}
        else:
            # No attachment analyses, return basic fallback
            if structure and isinstance(structure, dict):
                fallback = structure.copy()
                fallback["processing_status"] = "fallback_basic"
                fallback["error"] = "AI processing failed, using fallback result"
                return fallback
            else:
                return {"processing_status": "fallback_basic", "error": "AI processing failed"}

    def _has_mcp_support(self) -> bool:
        """Check if MCP integration is available and enabled."""
        return (self._mcp_manager is not None and 
                self._entry.options.get(CONF_ENABLE_MCP_INTEGRATION, True))

    async def _download_and_save_media(self, media_content_id: str) -> str:
        """Download and save media securely with comprehensive validation."""
        _LOGGER.debug("Processing media download request: %s", media_content_id)

        try:
            # Step 1: Validate input
            if not media_content_id or not isinstance(media_content_id, str):
                raise ValueError("Invalid media content ID")

            # Step 2: Resolve media source
            media = await async_resolve_media(self.hass, media_content_id, None)
            if not media or not hasattr(media, 'url'):
                raise ValueError("Failed to resolve media source")

            media_url = str(media.url)
            _LOGGER.debug("Resolved media URL: %s", media_url)

            # Step 3: Validate URL security
            if not _is_safe_url(media_url):
                raise ValueError(f"Unsafe or blocked URL: {media_url}")

            # Step 4: Check file extension from media content ID
            if not _is_allowed_extension(media_content_id):
                raise ValueError(f"File type not allowed: {media_content_id}")

            # Step 5: Download with security controls
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            async with self.hass.helpers.aiohttp_client.async_get_clientsession().get(
                media_url, timeout=timeout, headers={'User-Agent': 'HomeAssistant-GLMAgent/1.0'}
            ) as response:
                # Check response status
                if response.status != 200:
                    raise ValueError(f"Failed to download media: HTTP {response.status}")

                # Check content type
                content_type = response.headers.get('content-type', '').lower().split(';')[0]
                if content_type and content_type not in ALLOWED_MIME_TYPES:
                    raise ValueError(f"Content type not allowed: {content_type}")

                # Check content length
                content_length = response.headers.get('content-length')
                if content_length and int(content_length) > MAX_FILE_SIZE_BYTES:
                    raise ValueError(f"File too large: {content_length} bytes")

                # Download with size limit
                media_bytes = await response.read()

                # Double-check file size after download
                if len(media_bytes) > MAX_FILE_SIZE_BYTES:
                    raise ValueError(f"Downloaded file too large: {len(media_bytes)} bytes")

                if len(media_bytes) == 0:
                    raise ValueError("Downloaded file is empty")

            # Step 6: Generate secure filename
            filename = _generate_secure_filename(media_content_id)

            # Step 7: Create secure storage path
            ai_task_dir = os.path.join(self.hass.config.path("www"), "ai_task_media")

            # Ensure directory exists with proper permissions
            os.makedirs(ai_task_dir, exist_ok=True)

            # Step 7.5: Clean up old files (run in background, don't block)
            try:
                # Create a background task for cleanup
                self.hass.async_create_task(_cleanup_old_files(ai_task_dir))
            except Exception as e:
                _LOGGER.warning("Failed to start cleanup task: %s", e)

            # Verify directory is writable
            if not os.access(ai_task_dir, os.W_OK):
                raise ValueError(f"Directory not writable: {ai_task_dir}")

            # Check available disk space (at least 2x the file size)
            stat = os.statvfs(ai_task_dir)
            available_space = stat.f_frsize * stat.f_bavail
            if available_space < len(media_bytes) * 2:
                raise ValueError("Insufficient disk space")

            # Step 8: Write file securely
            file_path = os.path.join(ai_task_dir, filename)

            # Use temporary file and atomic rename
            temp_path = f"{file_path}.tmp"
            try:
                with open(temp_path, 'wb') as f:
                    f.write(media_bytes)
                    f.flush()  # Ensure data is written to disk
                    os.fsync(f.fileno())  # Force write to disk

                # Atomic rename to final filename
                os.rename(temp_path, file_path)

            except Exception as e:
                # Clean up temp file if something went wrong
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except OSError:
                        pass
                raise e

            _LOGGER.debug("Securely saved media to: %s", file_path)

            # Step 9: Generate public URL
            base_url = self._entry.options.get(CONF_HA_BASE_URL)
            if not base_url:
                # Default to Home Assistant's local URL (localhost:8123)
                base_url = "http://localhost:8123"

            # Validate base URL format
            if not base_url.startswith(('http://', 'https://')):
                raise ValueError(f"Invalid base URL format: {base_url}")

            public_url = f"{base_url.rstrip('/')}/local/ai_task_media/{filename}"

            _LOGGER.debug("Generated public URL: %s", public_url)
            return public_url

        except Exception as e:
            _LOGGER.error("Media download failed for %s: %s", media_content_id, e)
            # Re-raise with context for the caller
            raise ValueError(f"Failed to process media: {str(e)}") from e

    async def _analyze_media_with_mcp(self, public_url: str) -> str:
        """Analyze media using MCP with enhanced error handling."""
        _LOGGER.debug("Analyzing media via MCP: %s", public_url)

        if not self._mcp_manager:
            raise ValueError("MCP manager not available")

        try:
            # Validate the URL before processing
            if not public_url or not isinstance(public_url, str):
                raise ValueError("Invalid media URL for analysis")

            # Use timeout to prevent hanging
            analysis = await asyncio.wait_for(
                self._mcp_manager.analyze_image(
                    public_url,
                    prompt="Describe this image in detail for AI analysis"
                ),
                timeout=180.0  # 3 minutes max for image analysis
            )

            # Validate the analysis result
            if not analysis or not isinstance(analysis, str):
                raise ValueError("Invalid analysis result from MCP")

            # Truncate extremely long analyses
            max_analysis_length = 5000
            if len(analysis) > max_analysis_length:
                truncated_analysis = analysis[:max_analysis_length] + "... [truncated]"
                _LOGGER.warning("Analysis truncated from %d to %d characters",
                              len(analysis), max_analysis_length)
                return truncated_analysis

            _LOGGER.debug("MCP analysis completed successfully (%d characters)", len(analysis))
            return analysis

        except asyncio.TimeoutError:
            error_msg = f"MCP analysis timeout for {public_url}"
            _LOGGER.error(error_msg)
            raise TimeoutError(error_msg)

        except Exception as e:
            error_msg = f"MCP analysis failed: {str(e)}"
            _LOGGER.error(error_msg)
            # Re-raise with more context
            raise RuntimeError(error_msg) from e

    async def _get_entity_status(self) -> Dict[str, Any]:
        """Get comprehensive entity status for debugging."""
        try:
            return {
                "entity_id": self._attr_unique_id,
                "entity_name": self._attr_name,
                "available": self.available,
                "mcp_support": self._has_mcp_support(),
                "plan": self._entry.data.get("plan", "unknown"),
                "mcp_manager_available": self._mcp_manager is not None,
                "ai_agent_available": self._agent is not None,
                "www_directory_writable": self._check_www_directory_permissions()
            }
        except Exception as e:
            _LOGGER.error("Error getting entity status: %s", e)
            return {
                "error": f"Status check failed: {str(e)}",
                "entity_id": getattr(self, '_attr_unique_id', 'unknown'),
                "available": self.available
            }

    def _check_www_directory_permissions(self) -> Dict[str, Any]:
        """Check www directory permissions and available space."""
        try:
            www_path = self.hass.config.path("www")
            ai_task_dir = os.path.join(www_path, "ai_task_media")

            # Check if directories exist and are writable
            www_exists = os.path.exists(www_path)
            www_writable = www_exists and os.access(www_path, os.W_OK)

            ai_task_exists = os.path.exists(ai_task_dir)
            ai_task_writable = ai_task_exists and os.access(ai_task_dir, os.W_OK)

            # Check disk space if directory exists
            available_space = None
            if www_exists:
                stat = os.statvfs(www_path)
                available_space = stat.f_frsize * stat.f_bavail

            return {
                "www_directory_exists": www_exists,
                "www_directory_writable": www_writable,
                "ai_task_directory_exists": ai_task_exists,
                "ai_task_directory_writable": ai_task_writable,
                "available_space_bytes": available_space,
                "available_space_mb": round(available_space / (1024 * 1024), 2) if available_space else None
            }

        except Exception as e:
            return {
                "error": f"Permission check failed: {str(e)}",
                "www_directory_exists": False,
                "www_directory_writable": False
            }

    async def _broadcast_task_update(
        self,
        task: Any,
        result: Any,
        processing_time: float,
        successful_attachments: int
    ) -> None:
        """Broadcast AI task update via secure WebSocket.

        Args:
            task: The AI task that was processed
            result: The result of the task
            processing_time: Time taken to process the task
            successful_attachments: Number of successfully processed attachments
        """
        try:
            if hasattr(self, '_agent') and hasattr(self._agent, 'websocket_manager'):
                # Create task data for broadcasting
                task_data = {
                    "entity_id": self.entity_id,
                    "attributes": {
                        "task_name": task.task_name,
                        "task_status": "completed",
                        "processing_time": round(processing_time, 2),
                        "attachments_processed": successful_attachments,
                        "total_attachments": len(task.attachments or []),
                        "timestamp": datetime.now().isoformat(),
                        "has_result": result is not None,
                        "result_type": type(result).__name__ if result else None
                    },
                    "state": "completed"
                }

                # Add result metadata if available
                if isinstance(result, dict):
                    task_data["attributes"].update({
                        "result_keys": list(result.keys()) if result else [],
                        "has_error": result.get("processing_error", False) or result.get("critical_error", False)
                    })

                # Broadcast via WebSocket manager
                await self._agent.websocket_manager.broadcast_entity_update(
                    self.entity_id,
                    None,
                    task_data
                )

                _LOGGER.debug("AI Task update broadcasted via WebSocket: %s", task.task_name)

        except Exception as e:
            _LOGGER.error("Error broadcasting AI task update: %s", e)