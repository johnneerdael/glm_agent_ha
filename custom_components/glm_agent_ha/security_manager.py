"""Security management system for GLM Agent HA integration."""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import os
import re
import secrets
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union
from urllib.parse import urlparse

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN


class SecurityLevel(Enum):
    """Security levels for different operations."""
    LOW = "low"        # Basic operations
    MEDIUM = "medium"  # Sensitive operations
    HIGH = "high"      # Critical operations
    CRITICAL = "critical"  # Security-critical operations


class ThreatType(Enum):
    """Types of security threats."""
    INJECTION = "injection"
    XSS = "xss"
    CSRF = "csrf"
    PATH_TRAVERSAL = "path_traversal"
    DOS = "dos"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    DATA_EXFILTRATION = "data_exfiltration"
    MALICIOUS_INPUT = "malicious_input"


class SecurityEvent:
    """Security event for tracking and analysis."""

    def __init__(self, event_type: ThreatType, severity: SecurityLevel,
                 source: str, description: str, **kwargs):
        self.timestamp = datetime.utcnow()
        self.event_type = event_type
        self.severity = severity
        self.source = source
        self.description = description
        self.metadata = kwargs

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "source": self.source,
            "description": self.description,
            "metadata": self.metadata
        }


class GLMAgentSecurityManager:
    """Comprehensive security management system."""

    def __init__(self, hass: HomeAssistant):
        """Initialize the security manager.

        Args:
            hass: Home Assistant instance
        """
        self.hass = hass

        # Security configuration
        self.enable_rate_limiting = True
        self.enable_input_validation = True
        self.enable_threat_detection = True
        self.enable_audit_logging = True

        # Rate limiting
        self._rate_limits: Dict[str, Dict[str, Any]] = {}
        self._default_rate_limit = {
            "requests_per_minute": 60,
            "requests_per_hour": 1000,
            "requests_per_day": 10000
        }

        # Threat detection patterns
        self._injection_patterns = [
            r"(?i)(union|select|insert|update|delete|drop|create|alter)\s+",
            r"(?i)(script|javascript|vbscript|onload|onerror)\s*=",
            r"(?i)(\.\./|\.\.\\|%2e%2e%2f|%2e%2e\\)",
            r"(?i)(exec|eval|system|shell)\s*\(",
            r"(?i)(cmd|powershell|bash|sh)\s+",
            r"(?i)(<iframe|<object|<embed|<script)",
            r"(?i)(document\.|window\.|location\.)",
        ]

        # Allowed domains and IPs for external calls
        self._allowed_domains: Set[str] = {
            "api.openai.com",
            "api.z.ai",
            "context7.com",
            "jina.ai",
            "tavily.com",
            "api.github.com",
            "github.com",
            "supabase.com"
        }

        self._allowed_ip_ranges: List[str] = [
            "0.0.0.0/0",  # Allow all initially, can be restricted
        ]

        # Security events storage
        self._security_events: List[SecurityEvent] = []
        self._max_events = 10000

        # Blocked entities
        self._blocked_ips: Set[str] = set()
        self._blocked_user_agents: Set[str] = set()
        self._blocked_patterns: List[str] = []

        # API keys and tokens validation
        self._token_blacklist: Set[str] = set()
        self._suspicious_activities: Dict[str, int] = {}

        # File security
        self._allowed_extensions = {
            ".txt", ".md", ".json", ".yaml", ".yml", ".csv",
            ".jpg", ".jpeg", ".png", ".gif", ".webp",
            ".pdf", ".doc", ".docx", ".txt"
        }

        self._max_file_size = 50 * 1024 * 1024  # 50MB

        # Initialize security policies
        self._initialize_security_policies()

    def _initialize_security_policies(self) -> None:
        """Initialize security policies and configurations."""
        # Load security policies from environment variables
        self.enable_rate_limiting = os.environ.get("GLM_AGENT_RATE_LIMITING", "true").lower() == "true"
        self.enable_input_validation = os.environ.get("GLM_AGENT_INPUT_VALIDATION", "true").lower() == "true"
        self.enable_threat_detection = os.environ.get("GLM_AGENT_THREAT_DETECTION", "true").lower() == "true"
        self.enable_audit_logging = os.environ.get("GLM_AGENT_AUDIT_LOGGING", "true").lower() == "true"

        # Load allowed domains
        allowed_domains_env = os.environ.get("GLM_AGENT_ALLOWED_DOMAINS", "")
        if allowed_domains_env:
            self._allowed_domains.update(domain.strip() for domain in allowed_domains_env.split(","))

        # Load rate limit configuration
        rate_limit_env = os.environ.get("GLM_AGENT_RATE_LIMIT", "")
        if rate_limit_env:
            try:
                limits = json.loads(rate_limit_env)
                self._default_rate_limit.update(limits)
            except json.JSONDecodeError:
                pass  # Use defaults if invalid JSON

    def validate_input(self, input_data: str, input_type: str = "general",
                       max_length: int = 10000) -> tuple[bool, Optional[str]]:
        """Validate input data against security threats.

        Args:
            input_data: Input string to validate
            input_type: Type of input (general, prompt, filename, etc.)
            max_length: Maximum allowed length

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.enable_input_validation:
            return True, None

        # Check length
        if len(input_data) > max_length:
            self._log_security_event(
                ThreatType.MALICIOUS_INPUT,
                SecurityLevel.MEDIUM,
                "input_validation",
                f"Input too long: {len(input_data)} characters",
                input_type=input_type,
                length=len(input_data)
            )
            return False, f"Input too long (max {max_length} characters)"

        # Check for injection patterns
        for pattern in self._injection_patterns:
            if re.search(pattern, input_data):
                self._log_security_event(
                    ThreatType.INJECTION,
                    SecurityLevel.HIGH,
                    "input_validation",
                    f"Suspicious pattern detected: {pattern}",
                    input_type=input_type,
                    pattern=pattern
                )
                return False, "Input contains potentially malicious content"

        # Additional checks for specific input types
        if input_type == "filename":
            # Check for path traversal
            if ".." in input_data or input_data.startswith("/") or ":" in input_data:
                self._log_security_event(
                    ThreatType.PATH_TRAVERSAL,
                    SecurityLevel.HIGH,
                    "input_validation",
                    f"Path traversal attempt in filename: {input_data}",
                    filename=input_data
                )
                return False, "Invalid filename format"

            # Check file extension
            file_ext = os.path.splitext(input_data)[1].lower()
            if file_ext not in self._allowed_extensions:
                self._log_security_event(
                    ThreatType.MALICIOUS_INPUT,
                    SecurityLevel.MEDIUM,
                    "input_validation",
                    f"Disallowed file extension: {file_ext}",
                    filename=input_data,
                    extension=file_ext
                )
                return False, f"File extension not allowed: {file_ext}"

        elif input_type == "url":
            # Validate URL
            try:
                parsed = urlparse(input_data)
                if not parsed.scheme or not parsed.netloc:
                    return False, "Invalid URL format"

                # Check domain against allowed list
                if parsed.netloc not in self._allowed_domains:
                    self._log_security_event(
                        ThreatType.UNAUTHORIZED_ACCESS,
                        SecurityLevel.HIGH,
                        "input_validation",
                        f"Access to unauthorized domain: {parsed.netloc}",
                        url=input_data,
                        domain=parsed.netloc
                    )
                    return False, f"Domain not allowed: {parsed.netloc}"

            except Exception:
                return False, "Invalid URL format"

        return True, None

    def validate_file_upload(self, filename: str, file_size: int,
                           file_content: Optional[bytes] = None) -> tuple[bool, Optional[str]]:
        """Validate file upload for security threats.

        Args:
            filename: Name of the file
            file_size: Size of the file in bytes
            file_content: Optional file content for deeper inspection

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Validate filename
        is_valid, error = self.validate_input(filename, "filename", 255)
        if not is_valid:
            return False, error

        # Check file size
        if file_size > self._max_file_size:
            self._log_security_event(
                ThreatType.MALICIOUS_INPUT,
                SecurityLevel.MEDIUM,
                "file_upload",
                f"File too large: {file_size} bytes",
                filename=filename,
                size=file_size
            )
            return False, f"File too large (max {self._max_file_size // (1024*1024)}MB)"

        # Deep scan file content if provided
        if file_content and self.enable_threat_detection:
            # Check for malicious content in file
            content_str = file_content.decode('utf-8', errors='ignore')

            # Check for embedded scripts or executable content
            malicious_patterns = [
                r'(?i)<script[^>]*>',
                r'(?i)javascript:',
                r'(?i)vbscript:',
                r'(?i)onload\s*=',
                r'(?i)onerror\s*=',
                r'(?i)exec\s*\(',
                r'(?i)eval\s*\(',
                r'(?i)system\s*\(',
            ]

            for pattern in malicious_patterns:
                if re.search(pattern, content_str):
                    self._log_security_event(
                        ThreatType.INJECTION,
                        SecurityLevel.HIGH,
                        "file_upload",
                        f"Malicious content detected in file: {filename}",
                        filename=filename,
                        pattern=pattern
                    )
                    return False, "File contains potentially malicious content"

        return True, None

    def check_rate_limit(self, identifier: str, limit_type: str = "default") -> tuple[bool, Optional[Dict[str, Any]]]:
        """Check if identifier has exceeded rate limits.

        Args:
            identifier: Unique identifier (IP address, user ID, etc.)
            limit_type: Type of rate limit to check

        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        if not self.enable_rate_limiting:
            return True, None

        now = time.time()

        # Initialize rate limit tracking for identifier
        if identifier not in self._rate_limits:
            self._rate_limits[identifier] = {
                "requests": [],
                "blocked_until": 0
            }

        rate_limit_data = self._rate_limits[identifier]

        # Check if currently blocked
        if now < rate_limit_data["blocked_until"]:
            return False, {
                "blocked": True,
                "blocked_until": rate_limit_data["blocked_until"],
                "reason": "Rate limit exceeded"
            }

        # Get rate limits
        limits = self._default_rate_limit.copy()
        if limit_type != "default":
            # Could implement custom limits per type
            pass

        # Clean old requests (older than 24 hours)
        cutoff_time = now - 24 * 60 * 60
        rate_limit_data["requests"] = [
            req_time for req_time in rate_limit_data["requests"]
            if req_time > cutoff_time
        ]

        # Check rate limits
        recent_requests = rate_limit_data["requests"]

        # Check per-minute limit
        minute_ago = now - 60
        minute_count = sum(1 for req_time in recent_requests if req_time > minute_ago)
        if minute_count >= limits["requests_per_minute"]:
            block_time = now + 60  # Block for 1 minute
            rate_limit_data["blocked_until"] = block_time

            self._log_security_event(
                ThreatType.DOS,
                SecurityLevel.MEDIUM,
                "rate_limiting",
                f"Rate limit exceeded (per minute): {identifier}",
                identifier=identifier,
                minute_count=minute_count,
                limit=limits["requests_per_minute"]
            )
            return False, {
                "blocked": True,
                "blocked_until": block_time,
                "reason": "Per-minute rate limit exceeded",
                "count": minute_count,
                "limit": limits["requests_per_minute"]
            }

        # Check per-hour limit
        hour_ago = now - 3600
        hour_count = sum(1 for req_time in recent_requests if req_time > hour_ago)
        if hour_count >= limits["requests_per_hour"]:
            block_time = now + 300  # Block for 5 minutes
            rate_limit_data["blocked_until"] = block_time

            self._log_security_event(
                ThreatType.DOS,
                SecurityLevel.MEDIUM,
                "rate_limiting",
                f"Rate limit exceeded (per hour): {identifier}",
                identifier=identifier,
                hour_count=hour_count,
                limit=limits["requests_per_hour"]
            )
            return False, {
                "blocked": True,
                "blocked_until": block_time,
                "reason": "Per-hour rate limit exceeded",
                "count": hour_count,
                "limit": limits["requests_per_hour"]
            }

        # Check per-day limit
        day_count = len(recent_requests)
        if day_count >= limits["requests_per_day"]:
            block_time = now + 3600  # Block for 1 hour
            rate_limit_data["blocked_until"] = block_time

            self._log_security_event(
                ThreatType.DOS,
                SecurityLevel.HIGH,
                "rate_limiting",
                f"Rate limit exceeded (per day): {identifier}",
                identifier=identifier,
                day_count=day_count,
                limit=limits["requests_per_day"]
            )
            return False, {
                "blocked": True,
                "blocked_until": block_time,
                "reason": "Per-day rate limit exceeded",
                "count": day_count,
                "limit": limits["requests_per_day"]
            }

        # Record this request
        rate_limit_data["requests"].append(now)

        return True, {
            "blocked": False,
            "remaining_minute": limits["requests_per_minute"] - minute_count,
            "remaining_hour": limits["requests_per_hour"] - hour_count,
            "remaining_day": limits["requests_per_day"] - day_count
        }

    def validate_api_key(self, api_key: str, provider: str) -> tuple[bool, Optional[str]]:
        """Validate API key for security threats.

        Args:
            api_key: API key to validate
            provider: Provider name

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not api_key:
            return False, "API key is required"

        # Check if key is blacklisted
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        if key_hash in self._token_blacklist:
            self._log_security_event(
                ThreatType.UNAUTHORIZED_ACCESS,
                SecurityLevel.CRITICAL,
                "api_validation",
                f"Blacklisted API key used: {provider}",
                provider=provider,
                key_hash=key_hash[:16] + "..."
            )
            return False, "API key is not authorized"

        # Check key format (basic validation)
        if provider == "openai":
            if not api_key.startswith("sk-"):
                return False, "Invalid OpenAI API key format"
        elif provider == "z_ai":
            if len(api_key) < 20:  # Basic length check
                return False, "Invalid Z.AI API key format"

        # Additional validation could be added here
        # For example, checking against known compromised keys

        return True, None

    def detect_anomalous_activity(self, activity_type: str, identifier: str,
                                  metadata: Optional[Dict[str, Any]] = None) -> tuple[bool, Optional[str]]:
        """Detect anomalous activity patterns.

        Args:
            activity_type: Type of activity (login, api_call, file_upload, etc.)
            identifier: Unique identifier (user ID, IP address, etc.)
            metadata: Additional metadata for analysis

        Returns:
            Tuple of (is_anomalous, reason)
        """
        if not self.enable_threat_detection:
            return False, None

        # Track activity patterns
        key = f"{activity_type}:{identifier}"

        if key not in self._suspicious_activities:
            self._suspicious_activities[key] = 0

        self._suspicious_activities[key] += 1

        # Check for patterns indicating suspicious activity
        activity_count = self._suspicious_activities[key]

        # High frequency of the same activity
        if activity_count > 100:  # Threshold can be adjusted
            self._log_security_event(
                ThreatType.DOS,
                SecurityLevel.HIGH,
                "anomaly_detection",
                f"High frequency activity detected: {activity_type}",
                activity_type=activity_type,
                identifier=identifier,
                count=activity_count,
                metadata=metadata
            )
            return True, f"High frequency {activity_type} activity detected"

        # Unusual time patterns (e.g., activity at odd hours)
        current_hour = datetime.now().hour
        if activity_type == "api_call" and (current_hour < 6 or current_hour > 22):
            if activity_count > 10:  # Threshold for unusual hours
                self._log_security_event(
                    ThreatType.UNAUTHORIZED_ACCESS,
                    SecurityLevel.MEDIUM,
                    "anomaly_detection",
                    f"Unusual time activity: {activity_type}",
                    activity_type=activity_type,
                    identifier=identifier,
                    hour=current_hour,
                    count=activity_count
                )
                return True, f"Unusual time {activity_type} activity detected"

        return False, None

    def sanitize_data(self, data: Any, context: str = "general") -> Any:
        """Sanitize data to remove sensitive information.

        Args:
            data: Data to sanitize
            context: Context for sanitization rules

        Returns:
            Sanitized data
        """
        if isinstance(data, str):
            # Sanitize string data
            sanitized = data

            # Remove or mask common sensitive patterns
            sensitive_patterns = [
                (r'(sk-[A-Za-z0-9]{48})', 'sk-***REDACTED***'),
                (r'(Bearer\s+[A-Za-z0-9\-._~+/]+=*)', 'Bearer ***REDACTED***'),
                (r'(token["\']?\s*[:=]\s*["\']?)([A-Za-z0-9\-._~+/]+=*["\']?)', r'\1***REDACTED***'),
                (r'(password["\']?\s*[:=]\s*["\']?)([^"\'\s]+)', r'\1***REDACTED***'),
                (r'(secret["\']?\s*[:=]\s*["\']?)([^"\'\s]+)', r'\1***REDACTED***'),
                (r'(key["\']?\s*[:=]\s*["\']?)([A-Za-z0-9\-._~+/]+=*["\']?)', r'\1***REDACTED***'),
            ]

            for pattern, replacement in sensitive_patterns:
                sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)

            return sanitized

        elif isinstance(data, dict):
            # Sanitize dictionary recursively
            sanitized = {}
            for key, value in data.items():
                # Check if key indicates sensitive data
                if any(sensitive in key.lower() for sensitive in
                      ['token', 'key', 'password', 'secret', 'credential', 'auth']):
                    sanitized[key] = "***REDACTED***"
                else:
                    sanitized[key] = self.sanitize_data(value, context)
            return sanitized

        elif isinstance(data, list):
            # Sanitize list recursively
            return [self.sanitize_data(item, context) for item in data]

        else:
            return data

    def generate_secure_token(self, length: int = 32) -> str:
        """Generate a cryptographically secure random token.

        Args:
            length: Length of token to generate

        Returns:
            Secure random token
        """
        return secrets.token_urlsafe(length)

    def hash_sensitive_data(self, data: str, salt: Optional[str] = None) -> str:
        """Hash sensitive data using secure algorithm.

        Args:
            data: Data to hash
            salt: Optional salt for hashing

        Returns:
            Hashed data
        """
        if salt is None:
            salt = secrets.token_hex(16)

        return hashlib.pbkdf2_hmac('sha256', data.encode(), salt.encode(), 100000).hex()

    def _log_security_event(self, event_type: ThreatType, severity: SecurityLevel,
                           source: str, description: str, **kwargs) -> None:
        """Log security event.

        Args:
            event_type: Type of security event
            severity: Severity level
            source: Source of the event
            description: Event description
            **kwargs: Additional metadata
        """
        if not self.enable_audit_logging:
            return

        event = SecurityEvent(event_type, severity, source, description, **kwargs)
        self._security_events.append(event)

        # Maintain maximum number of events
        if len(self._security_events) > self._max_events:
            self._security_events = self._security_events[-self._max_events:]

        # Log to structured logger if available
        try:
            structured_logger = self.hass.data[DOMAIN].get("structured_logger")
            if structured_logger:
                structured_logger.security_event(
                    event_type=event_type.value,
                    severity=severity.value,
                    details=event.to_dict()
                )
        except Exception:
            pass  # Fallback silently if structured logger unavailable

    def get_security_report(self, hours: int = 24) -> Dict[str, Any]:
        """Generate comprehensive security report.

        Args:
            hours: Number of hours to include in report

        Returns:
            Security report data
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        # Filter recent events
        recent_events = [
            event for event in self._security_events
            if event.timestamp > cutoff_time
        ]

        # Generate statistics
        event_counts = {}
        severity_counts = {}
        source_counts = {}

        for event in recent_events:
            event_counts[event.event_type.value] = event_counts.get(event.event_type.value, 0) + 1
            severity_counts[event.severity.value] = severity_counts.get(event.severity.value, 0) + 1
            source_counts[event.source] = source_counts.get(event.source, 0) + 1

        # Generate recommendations
        recommendations = []

        if severity_counts.get("CRITICAL", 0) > 0:
            recommendations.append("🚨 CRITICAL security events detected - immediate attention required")

        if severity_counts.get("HIGH", 0) > 5:
            recommendations.append("⚠️ High number of HIGH severity events - review security configuration")

        if event_counts.get("dos", 0) > 10:
            recommendations.append("🛡️ Multiple DoS attempts detected - consider stricter rate limiting")

        if event_counts.get("injection", 0) > 0:
            recommendations.append("🔍 Injection attempts detected - review input validation")

        if not recommendations:
            recommendations.append("✅ No significant security issues detected")

        return {
            "report_timestamp": datetime.utcnow().isoformat(),
            "period_hours": hours,
            "total_events": len(recent_events),
            "event_counts": event_counts,
            "severity_counts": severity_counts,
            "source_counts": source_counts,
            "recommendations": recommendations,
            "blocked_ips": list(self._blocked_ips),
            "blocked_user_agents": list(self._blocked_user_agents),
            "rate_limit_active": len(self._rate_limits),
            "security_features": {
                "rate_limiting_enabled": self.enable_rate_limiting,
                "input_validation_enabled": self.enable_input_validation,
                "threat_detection_enabled": self.enable_threat_detection,
                "audit_logging_enabled": self.enable_audit_logging
            }
        }

    def block_identifier(self, identifier: str, reason: str, duration_hours: int = 24) -> None:
        """Block an identifier for security reasons.

        Args:
            identifier: Identifier to block (IP address, user agent, etc.)
            reason: Reason for blocking
            duration_hours: Duration of block in hours
        """
        self._blocked_ips.add(identifier)

        # Log blocking event
        self._log_security_event(
            ThreatType.UNAUTHORIZED_ACCESS,
            SecurityLevel.HIGH,
            "manual_block",
            f"Identifier blocked: {identifier}",
            identifier=identifier,
            reason=reason,
            duration_hours=duration_hours
        )

    def is_blocked(self, identifier: str) -> bool:
        """Check if identifier is blocked.

        Args:
            identifier: Identifier to check

        Returns:
            True if blocked
        """
        return identifier in self._blocked_ips

    def get_allowed_domains(self) -> Set[str]:
        """Get list of allowed domains for external calls.

        Returns:
            Set of allowed domains
        """
        return self._allowed_domains.copy()

    def add_allowed_domain(self, domain: str) -> None:
        """Add domain to allowed list.

        Args:
            domain: Domain to add
        """
        self._allowed_domains.add(domain.lower())

        self._log_security_event(
            ThreatType.UNAUTHORIZED_ACCESS,
            SecurityLevel.LOW,
            "domain_management",
            f"Domain added to allowlist: {domain}",
            domain=domain
        )

    def remove_allowed_domain(self, domain: str) -> None:
        """Remove domain from allowed list.

        Args:
            domain: Domain to remove
        """
        self._allowed_domains.discard(domain.lower())

        self._log_security_event(
            ThreatType.UNAUTHORIZED_ACCESS,
            SecurityLevel.MEDIUM,
            "domain_management",
            f"Domain removed from allowlist: {domain}",
            domain=domain
        )

    def clear_security_events(self) -> None:
        """Clear all security events."""
        self._security_events.clear()

        self._log_security_event(
            ThreatType.UNAUTHORIZED_ACCESS,
            SecurityLevel.LOW,
            "maintenance",
            "Security events cleared"
        )