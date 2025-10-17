"""Structured logging system for GLM Agent HA integration."""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import traceback
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from homeassistant.core import HomeAssistant


class LogLevel(Enum):
    """Log levels for structured logging."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogCategory(Enum):
    """Log categories for better organization."""
    SYSTEM = "system"
    AI_AGENT = "ai_agent"
    MCP_INTEGRATION = "mcp_integration"
    AI_TASK_ENTITY = "ai_task_entity"
    PERFORMANCE = "performance"
    SECURITY = "security"
    CONFIG = "config"
    API = "api"
    CACHE = "cache"
    ERROR = "error"


class GLMAgentStructuredLogger:
    """Structured logger with enhanced formatting and filtering capabilities."""

    def __init__(self, hass: HomeAssistant, name: str = "glm_agent_ha"):
        """Initialize the structured logger.

        Args:
            hass: Home Assistant instance
            name: Logger name (typically the component name)
        """
        self.hass = hass
        self.name = name
        self.logger = logging.getLogger(name)

        # Configuration
        self.enable_structured_output = self._get_env_bool("GLM_AGENT_STRUCTURED_LOGS", True)
        self.enable_file_logging = self._get_env_bool("GLM_AGENT_FILE_LOGS", False)
        self.log_file_path = os.environ.get("GLM_AGENT_LOG_FILE", "")
        self.max_log_file_size = int(os.environ.get("GLM_AGENT_MAX_LOG_SIZE", "10485760"))  # 10MB
        self.enable_console_colors = self._get_env_bool("GLM_AGENT_COLOR_LOGS", True)

        # Context tracking
        self._request_context = {}
        self._session_id = self._generate_session_id()
        self._correlation_id = None

        # Performance tracking
        self._log_counts = {level.value: 0 for level in LogLevel}
        self._category_counts = {category.value: 0 for category in LogCategory}

        # Security filtering
        self._sensitive_keys = {
            "token", "key", "password", "secret", "credential", "auth",
            "openai_token", "api_key", "access_token", "refresh_token"
        }

        self._setup_file_logging()
        self.logger.info("Structured logger initialized for %s", name)

    def _get_env_bool(self, env_var: str, default: bool = False) -> bool:
        """Get boolean value from environment variable."""
        return os.environ.get(env_var, "").lower() in ("true", "1", "yes", "on")

    def _generate_session_id(self) -> str:
        """Generate a unique session ID."""
        return f"session_{int(time.time())}_{os.getpid()}"

    def _setup_file_logging(self) -> None:
        """Set up file logging if enabled."""
        if not self.enable_file_logging or not self.log_file_path:
            return

        try:
            # Create log directory if it doesn't exist
            log_dir = os.path.dirname(self.log_file_path)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)

            # Set up file handler
            file_handler = logging.FileHandler(self.log_file_path, mode='a', encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)

            # Create formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)

            # Add handler to logger
            self.logger.addHandler(file_handler)
            self.logger.info("File logging enabled: %s", self.log_file_path)

        except Exception as e:
            self.logger.warning("Failed to set up file logging: %s", e)

    def set_correlation_id(self, correlation_id: str) -> None:
        """Set correlation ID for request tracking."""
        self._correlation_id = correlation_id

    def set_request_context(self, context: Dict[str, Any]) -> None:
        """Set request context for logging."""
        self._request_context.update(context)

    def clear_request_context(self) -> None:
        """Clear current request context."""
        self._request_context.clear()
        self._correlation_id = None

    def _sanitize_data(self, data: Any) -> Any:
        """Sanitize sensitive data from logs."""
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                if any(sensitive in key.lower() for sensitive in self._sensitive_keys):
                    sanitized[key] = "***REDACTED***"
                else:
                    sanitized[key] = self._sanitize_data(value)
            return sanitized
        elif isinstance(data, list):
            return [self._sanitize_data(item) for item in data]
        elif isinstance(data, str):
            # Basic pattern detection for potential sensitive data
            if any(pattern in data.lower() for pattern in ["token", "key", "secret", "password"]):
                return "***REDACTED***"
        return data

    def _create_log_entry(self, level: LogLevel, category: LogCategory,
                         message: str, **kwargs) -> Dict[str, Any]:
        """Create a structured log entry."""
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": level.value,
            "category": category.value,
            "logger": self.name,
            "message": message,
            "session_id": self._session_id,
        }

        # Add correlation ID if available
        if self._correlation_id:
            log_entry["correlation_id"] = self._correlation_id

        # Add request context
        if self._request_context:
            log_entry["context"] = self._sanitize_data(self._request_context)

        # Add additional fields
        sanitized_kwargs = self._sanitize_data(kwargs)
        log_entry.update(sanitized_kwargs)

        return log_entry

    def _format_for_console(self, log_entry: Dict[str, Any]) -> str:
        """Format log entry for console output."""
        if not self.enable_structured_output:
            # Traditional log format
            parts = [
                log_entry["timestamp"][:19],  # Remove microseconds and Z
                f"[{log_entry['category']}]",
                f"[{log_entry['level']}]",
                log_entry["message"]
            ]

            # Add key context info
            if "correlation_id" in log_entry:
                parts.append(f"[{log_entry['correlation_id'][:12]}]")

            return " ".join(parts)

        # Structured format
        color_code = ""
        reset_code = ""

        if self.enable_console_colors:
            colors = {
                LogLevel.DEBUG: "\033[36m",    # Cyan
                LogLevel.INFO: "\033[32m",     # Green
                LogLevel.WARNING: "\033[33m",  # Yellow
                LogLevel.ERROR: "\033[31m",    # Red
                LogLevel.CRITICAL: "\033[35m", # Magenta
            }
            reset_code = "\033[0m"
            color_code = colors.get(LogLevel(log_entry["level"]), "")

        # Create compact structured format
        essential_fields = {
            "ts": log_entry["timestamp"][:19],
            "cat": log_entry["category"],
            "lvl": log_entry["level"][0],  # First letter only
            "msg": log_entry["message"]
        }

        if "correlation_id" in log_entry:
            essential_fields["cid"] = log_entry["correlation_id"][:8]

        if "duration_ms" in log_entry:
            essential_fields["dur"] = f"{log_entry['duration_ms']}ms"

        if "error_type" in log_entry:
            essential_fields["err"] = log_entry["error_type"]

        formatted = f"{color_code}{json.dumps(essential_fields, separators=(',', ':'))}{reset_code}"
        return formatted

    def _log(self, level: LogLevel, category: LogCategory, message: str,
             exc_info: bool = False, **kwargs) -> None:
        """Internal logging method."""
        # Update counters
        self._log_counts[level.value] += 1
        self._category_counts[category.value] += 1

        # Create log entry
        log_entry = self._create_log_entry(level, category, message, **kwargs)

        # Format and log
        formatted_message = self._format_for_console(log_entry)

        # Log using standard Python logging
        log_method = getattr(self.logger, level.value.lower())
        log_method(formatted_message, exc_info=exc_info)

        # Check for log file rotation
        if self.enable_file_logging and self.log_file_path:
            self._check_log_rotation()

    def _check_log_rotation(self) -> None:
        """Check if log file needs rotation."""
        if not self.log_file_path or not os.path.exists(self.log_file_path):
            return

        try:
            file_size = os.path.getsize(self.log_file_path)
            if file_size > self.max_log_file_size:
                # Rotate log file
                backup_path = f"{self.log_file_path}.old"
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                os.rename(self.log_file_path, backup_path)
                self.logger.info("Log file rotated: %s -> %s", self.log_file_path, backup_path)
        except Exception as e:
            self.logger.warning("Failed to rotate log file: %s", e)

    # Public logging methods
    def debug(self, message: str, category: LogCategory = LogCategory.SYSTEM, **kwargs) -> None:
        """Log debug message."""
        self._log(LogLevel.DEBUG, category, message, **kwargs)

    def info(self, message: str, category: LogCategory = LogCategory.SYSTEM, **kwargs) -> None:
        """Log info message."""
        self._log(LogLevel.INFO, category, message, **kwargs)

    def warning(self, message: str, category: LogCategory = LogCategory.SYSTEM, **kwargs) -> None:
        """Log warning message."""
        self._log(LogLevel.WARNING, category, message, **kwargs)

    def error(self, message: str, category: LogCategory = LogCategory.ERROR, exc_info: bool = True, **kwargs) -> None:
        """Log error message."""
        self._log(LogLevel.ERROR, category, message, exc_info=exc_info, **kwargs)

    def critical(self, message: str, category: LogCategory = LogCategory.ERROR, exc_info: bool = True, **kwargs) -> None:
        """Log critical message."""
        self._log(LogLevel.CRITICAL, category, message, exc_info=exc_info, **kwargs)

    # Specialized logging methods
    def api_request(self, method: str, url: str, status_code: Optional[int] = None,
                   duration_ms: Optional[float] = None, **kwargs) -> None:
        """Log API request."""
        message = f"API {method} {url}"
        if status_code:
            message += f" -> {status_code}"

        log_data = {
            "method": method,
            "url": url,
            "status_code": status_code,
            "duration_ms": duration_ms
        }
        log_data.update(kwargs)

        level = LogLevel.INFO if status_code and 200 <= status_code < 300 else LogLevel.WARNING
        self._log(level, LogCategory.API, message, **log_data)

    def ai_request(self, request_type: str, provider: str, model: Optional[str] = None,
                  tokens_used: Optional[int] = None, duration_ms: Optional[float] = None,
                  success: bool = True, error_type: Optional[str] = None, **kwargs) -> None:
        """Log AI request."""
        message = f"AI {request_type} via {provider}"
        if model:
            message += f" ({model})"
        if not success:
            message += f" - FAILED"

        log_data = {
            "request_type": request_type,
            "provider": provider,
            "model": model,
            "tokens_used": tokens_used,
            "duration_ms": duration_ms,
            "success": success,
            "error_type": error_type
        }
        log_data.update(kwargs)

        level = LogLevel.INFO if success else LogLevel.ERROR
        self._log(level, LogCategory.AI_AGENT, message, **log_data)

    def mcp_operation(self, operation: str, server: str, success: bool = True,
                     duration_ms: Optional[float] = None, **kwargs) -> None:
        """Log MCP operation."""
        message = f"MCP {operation} on {server}"
        if not success:
            message += " - FAILED"

        log_data = {
            "operation": operation,
            "server": server,
            "success": success,
            "duration_ms": duration_ms
        }
        log_data.update(kwargs)

        level = LogLevel.INFO if success else LogLevel.ERROR
        self._log(level, LogCategory.MCP_INTEGRATION, message, **log_data)

    def performance_metric(self, metric_name: str, value: float, unit: str = "",
                          **kwargs) -> None:
        """Log performance metric."""
        message = f"Performance: {metric_name} = {value}"
        if unit:
            message += f" {unit}"

        log_data = {
            "metric_name": metric_name,
            "value": value,
            "unit": unit
        }
        log_data.update(kwargs)

        self._log(LogLevel.DEBUG, LogCategory.PERFORMANCE, message, **log_data)

    def security_event(self, event_type: str, severity: str = "info",
                      details: Optional[Dict[str, Any]] = None, **kwargs) -> None:
        """Log security event."""
        message = f"Security: {event_type}"

        log_data = {
            "event_type": event_type,
            "severity": severity,
            "details": details or {}
        }
        log_data.update(kwargs)

        level = LogLevel.WARNING if severity in ["medium", "high"] else LogLevel.INFO
        self._log(level, LogCategory.SECURITY, message, **log_data)

    def config_change(self, component: str, change_type: str, old_value: Any = None,
                     new_value: Any = None, **kwargs) -> None:
        """Log configuration change."""
        message = f"Config {component}: {change_type}"

        log_data = {
            "component": component,
            "change_type": change_type,
            "old_value": old_value,
            "new_value": new_value
        }
        log_data.update(kwargs)

        self._log(LogLevel.INFO, LogCategory.CONFIG, message, **log_data)

    def get_statistics(self) -> Dict[str, Any]:
        """Get logging statistics."""
        return {
            "session_id": self._session_id,
            "log_counts": self._log_counts.copy(),
            "category_counts": self._category_counts.copy(),
            "total_logs": sum(self._log_counts.values()),
            "structured_output_enabled": self.enable_structured_output,
            "file_logging_enabled": self.enable_file_logging,
            "log_file_path": self.log_file_path if self.enable_file_logging else None
        }

    def search_logs(self, query: str, category: Optional[LogCategory] = None,
                   level: Optional[LogLevel] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Search recent logs (simplified implementation)."""
        # This is a basic implementation - in a real scenario, you'd query the log files
        # or a log aggregation system
        results = []

        # For now, return empty results - this would need file reading implementation
        return results


# Context manager for request logging
class RequestContext:
    """Context manager for request-scoped logging."""

    def __init__(self, logger: GLMAgentStructuredLogger,
                 correlation_id: Optional[str] = None, **context):
        """Initialize request context.

        Args:
            logger: Structured logger instance
            correlation_id: Optional correlation ID for request tracking
            **context: Additional context fields
        """
        self.logger = logger
        self.correlation_id = correlation_id or f"req_{int(time.time() * 1000)}"
        self.context = context
        self.old_correlation_id = None
        self.old_context = None

    def __enter__(self):
        """Enter request context."""
        # Store old context
        self.old_correlation_id = self.logger._correlation_id
        self.old_context = self.logger._request_context.copy()

        # Set new context
        self.logger.set_correlation_id(self.correlation_id)
        self.logger.set_request_context(self.context)

        self.logger.debug("Request started", LogCategory.SYSTEM,
                         correlation_id=self.correlation_id)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit request context."""
        # Log request completion
        if exc_type is not None:
            self.logger.error("Request failed", LogCategory.ERROR,
                            correlation_id=self.correlation_id,
                            error_type=exc_type.__name__,
                            error_message=str(exc_val))
        else:
            self.logger.debug("Request completed successfully", LogCategory.SYSTEM,
                             correlation_id=self.correlation_id)

        # Restore old context
        self.logger.set_correlation_id(self.old_correlation_id)
        self.logger._request_context.clear()
        self.logger._request_context.update(self.old_context)

        # Don't suppress exceptions
        return False


# Performance monitoring decorator
def log_performance(logger: GLMAgentStructuredLogger, operation_name: str):
    """Decorator to log performance of functions."""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                logger.performance_metric(
                    operation_name, duration_ms, "ms",
                    success=True
                )
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.performance_metric(
                    operation_name, duration_ms, "ms",
                    success=False,
                    error_type=type(e).__name__
                )
                raise
        return async_wrapper
    return decorator


# Global logger instance management
_loggers: Dict[str, GLMAgentStructuredLogger] = {}

def get_logger(hass: HomeAssistant, name: str = "glm_agent_ha") -> GLMAgentStructuredLogger:
    """Get or create a structured logger instance."""
    if name not in _loggers:
        _loggers[name] = GLMAgentStructuredLogger(hass, name)
    return _loggers[name]

def cleanup_loggers() -> None:
    """Clean up logger instances."""
    _loggers.clear()