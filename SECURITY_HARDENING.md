# Security Hardening Guide for GLM Agent HA

This document covers the comprehensive security hardening measures implemented in GLM Agent HA to protect against various security threats and ensure safe operation.

## Overview

The security hardening system provides:
- **Input Validation**: Comprehensive validation and sanitization of all user inputs
- **Rate Limiting**: Protection against abuse and DoS attacks
- **Threat Detection**: Automated detection of suspicious activities and patterns
- **Access Control**: Management of allowed domains and blocked identifiers
- **Data Sanitization**: Automatic removal of sensitive information from logs and responses
- **Security Auditing**: Comprehensive logging and monitoring of security events

## Security Architecture

### Multi-Layer Security Model

1. **Input Validation Layer**: Validates all incoming data for malicious patterns
2. **Rate Limiting Layer**: Prevents abuse through request throttling
3. **Threat Detection Layer**: Identifies anomalous behavior patterns
4. **Access Control Layer**: Manages allowed domains and blocked entities
5. **Data Protection Layer**: Sanitizes sensitive data throughout the system
6. **Audit Layer**: Logs and monitors all security-relevant events

## Security Features

### 1. Input Validation

#### Comprehensive Pattern Detection
The system detects and blocks:
- **SQL Injection**: `UNION`, `SELECT`, `INSERT`, `UPDATE`, `DELETE` patterns
- **Cross-Site Scripting (XSS)**: `<script>`, `javascript:`, `onload`, `onerror`
- **Path Traversal**: `../`, `%2e%2e%2f`, absolute paths
- **Command Injection**: `exec(`, `eval(`, `system(`, `cmd|powershell|bash`
- **File Upload Threats**: Malicious scripts, embedded executables

#### Input Type Validation
- **General Text**: Length limits, character validation
- **Filenames**: Path safety, extension validation
- **URLs**: Domain validation, protocol checking
- **API Keys**: Format validation, blacklist checking

### 2. Rate Limiting

#### Configurable Rate Limits
- **Per Minute**: 60 requests (configurable)
- **Per Hour**: 1,000 requests (configurable)
- **Per Day**: 10,000 requests (configurable)

#### Intelligent Rate Limiting
- **Client Identification**: IP address, user ID, or combination
- **Progressive Blocking**: Increasing block durations for repeat offenders
- **Automatic Unblocking**: Blocks expire after configured duration
- **Exception Handling**: Legitimate users can request manual review

### 3. Threat Detection

#### Anomaly Detection Patterns
- **High Frequency Activity**: Unusual request patterns
- **Time-Based Anomalies**: Activity during unusual hours
- **Behavioral Deviations**: Departure from normal usage patterns
- **Error Rate Spikes**: Sudden increases in failed requests

#### Threat Categories
- **Injection Attacks**: SQL, XSS, command injection attempts
- **Denial of Service**: Rate limiting violations, resource abuse
- **Unauthorized Access**: Blocked entities attempting access
- **Data Exfiltration**: Suspicious data access patterns
- **Malicious Input**: Known attack patterns and payloads

### 4. Access Control

#### Domain Allowlisting
- **Default Safe Domains**: Pre-approved external service domains
- **Dynamic Management**: Add/remove domains through services
- **Protocol Validation**: Ensure HTTPS-only communications
- **Certificate Verification**: Validate SSL/TLS certificates

#### Identifier Blocking
- **IP Address Blocking**: Block malicious or abusive IPs
- **User Agent Blocking**: Block suspicious client signatures
- **Pattern Blocking**: Block based on behavioral patterns
- **Manual Controls**: Administrator-controlled blocking

### 5. Data Protection

#### Automatic Sanitization
- **API Key Redaction**: Replace with `***REDACTED***`
- **Password Masking**: Remove or mask sensitive credentials
- **Token Protection**: Secure handling of authentication tokens
- **PII Protection**: Personally Identifiable Information handling

#### Secure Token Management
- **Cryptographically Secure Generation**: Use `secrets` module
- **Secure Hashing**: PBKDF2 with salt for sensitive data
- **Token Rotation**: Regular rotation of authentication tokens
- **Blacklist Management**: Track compromised tokens

## Security Services

### 1. `glm_agent_ha.security_report`

Generate comprehensive security reports.

**Usage:**
```yaml
service: glm_agent_ha.security_report
data:
  hours: 24  # Optional: report period in hours (default: 24)
```

**Returns:**
```json
{
  "report_timestamp": "2025-01-14T10:30:00.000000",
  "period_hours": 24,
  "total_events": 15,
  "event_counts": {
    "dos": 5,
    "injection": 3,
    "unauthorized_access": 4,
    "malicious_input": 3
  },
  "severity_counts": {
    "LOW": 2,
    "MEDIUM": 8,
    "HIGH": 4,
    "CRITICAL": 1
  },
  "source_counts": {
    "input_validation": 8,
    "rate_limiting": 5,
    "anomaly_detection": 2
  },
  "recommendations": [
    "🚨 CRITICAL security events detected - immediate attention required",
    "⚠️ High number of HIGH severity events - review security configuration"
  ],
  "blocked_ips": ["192.168.1.100"],
  "blocked_user_agents": ["malicious-bot/1.0"],
  "rate_limit_active": 3,
  "security_features": {
    "rate_limiting_enabled": true,
    "input_validation_enabled": true,
    "threat_detection_enabled": true,
    "audit_logging_enabled": true
  }
}
```

### 2. `glm_agent_ha.security_validate`

Validate input data against security threats.

**Usage:**
```yaml
service: glm_agent_ha.security_validate
data:
  input: " DROP TABLE users; --"
  type: "general"  # Optional: general, prompt, filename, url
```

**Returns:**
```json
{
  "input_type": "general",
  "input_length": 25,
  "is_valid": false,
  "error_message": "Input contains potentially malicious content"
}
```

### 3. `glm_agent_ha.security_block`

Manually block identifiers for security reasons.

**Usage:**
```yaml
service: glm_agent_ha.security_block
data:
  identifier: "192.168.1.100"  # IP address or user ID
  reason: "Suspicious activity detected"
  duration: 24  # Hours
```

**Returns:**
```json
{
  "identifier": "192.168.1.100",
  "reason": "Suspicious activity detected",
  "duration_hours": 24,
  "blocked_at": "2025-01-14T10:30:00.000000"
}
```

### 4. `glm_agent_ha.security_domains`

Manage allowed domains for external calls.

**List Allowed Domains:**
```yaml
service: glm_agent_ha.security_domains
data:
  action: "list"
```

**Add Domain:**
```yaml
service: glm_agent_ha.security_domains
data:
  action: "add"
  domain: "api.trusted-service.com"
```

**Remove Domain:**
```yaml
service: glm_agent_ha.security_domains
data:
  action: "remove"
  domain: "api.suspicious-service.com"
```

## Configuration

### Environment Variables

Configure security features with environment variables:

```bash
# Enable rate limiting (default: true)
GLM_AGENT_RATE_LIMITING=true

# Enable input validation (default: true)
GLM_AGENT_INPUT_VALIDATION=true

# Enable threat detection (default: true)
GLM_AGENT_THREAT_DETECTION=true

# Enable audit logging (default: true)
GLM_AGENT_AUDIT_LOGGING=true

# Configure allowed domains (comma-separated)
GLM_AGENT_ALLOWED_DOMAINS=api.openai.com,api.z.ai,context7.com

# Configure rate limits (JSON format)
GLM_AGENT_RATE_LIMIT={"requests_per_minute": 60, "requests_per_hour": 1000}
```

### Home Assistant Configuration

Add to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.glm_agent_ha.security: debug  # Enable security logging
```

## Security Best Practices

### 1. Input Validation

```python
# Always validate user input
from .security_manager import GLMAgentSecurityManager

security_manager = GLMAAgentSecurityManager(hass)

def process_user_input(user_input):
    is_valid, error = security_manager.validate_input(user_input, "prompt", 5000)
    if not is_valid:
        raise ValueError(f"Invalid input: {error}")
    # Continue processing
```

### 2. Rate Limiting

```python
# Check rate limits before processing
client_id = get_client_identifier()
is_allowed, rate_info = security_manager.check_rate_limit(client_id)

if not is_allowed:
    return {"error": "Rate limit exceeded", "retry_after": rate_info.get("blocked_until")}
```

### 3. Data Sanitization

```python
# Sanitize data before logging or returning
sanitized_data = security_manager.sanitize_data(user_data, "api_response")

# Or use context-aware sanitization
sanitized_config = security_manager.sanitize_data(config_data, "configuration")
```

### 4. Security Event Logging

```python
# Log security events
security_manager._log_security_event(
    ThreatType.INJECTION,
    SecurityLevel.HIGH,
    "api_handler",
    "SQL injection attempt blocked",
    user_id=user_id,
    input_data=suspicious_input
)
```

## Threat Response Procedures

### 1. Injection Attacks

**Detection:**
- SQL patterns in input
- Command injection attempts
- XSS payloads

**Response:**
1. Immediately block the request
2. Log the security event
3. Consider temporary IP blocking
4. Alert administrators

### 2. Rate Limiting Violations

**Detection:**
- Exceeded per-minute limits
- High-frequency requests
- Repeated failed attempts

**Response:**
1. Implement progressive blocking
2. Increase block duration for repeat offenders
3. Log pattern of abuse
4. Consider CAPTCHA requirements

### 3. Unauthorized Access

**Detection:**
- Blocked entities attempting access
- API key validation failures
- Domain violations

**Response:**
1. Deny access immediately
2. Log security event
3. Investigate access patterns
4. Update block lists as needed

### 4. Data Exfiltration

**Detection:**
- Unusual data access patterns
- Large data transfers
- Suspicious query patterns

**Response:**
1. Monitor data access patterns
2. Log anomalous activities
3. Implement data transfer limits
4. Alert on suspicious behavior

## Security Monitoring

### Automated Monitoring

```yaml
# Security alert automation
alias: GLM Agent HA Security Alert
trigger:
  - platform: event
    event_type: glm_agent_ha_security_event
    event_data:
      severity: CRITICAL
action:
  - service: notify.persistent_notification
    data:
      title: "🚨 GLM Agent HA Security Alert"
      message: >
        Critical security event: {{ trigger.event_data.description }}
        Type: {{ trigger.event_data.event_type }}
        Source: {{ trigger.event.data.source }}
        Time: {{ trigger.event_data.timestamp }}
      data:
        tag: "glm_agent_ha_security_critical"
```

### Security Dashboard

```yaml
# Security metrics sensor
template:
  - sensor:
      - name: "GLM Agent HA Security Events"
        unit_of_measurement: "events"
        state_class: total_increasing
        state: >-
          {{ state_attr('sensor.glm_agent_ha_security_report', 'total_events') }}
      - name: "GLM Agent HA Blocked IPs"
        unit_of_measurement: "ips"
        state: >-
          {{ state_attr('sensor.glm_agent_ha_security_report', 'blocked_ips') | length }}
```

## Incident Response

### Security Incident Categories

#### Low Severity
- Occasional failed validation
- Minor rate limiting
- Suspicious but harmless patterns

**Response:**
1. Monitor for escalation
2. Log events for analysis
3. No immediate action required

#### Medium Severity
- Repeated injection attempts
- Rate limiting violations
- Domain violations

**Response:**
1. Implement temporary blocking
2. Increase monitoring
3. Review security configuration
4. Consider user notification

#### High Severity
- Successful injection attacks
- Persistent abuse patterns
- Multiple security violations

**Response:**
1. Immediate blocking
2. Administrator notification
3. Detailed incident logging
4. Security configuration review

#### Critical Severity
- System compromise indicators
- Data breach attempts
- Successful privilege escalation

**Response:**
1. Emergency blocking
2. Immediate administrator notification
3. Full security audit
4. Consider service shutdown

## Compliance and Auditing

### Security Audit Checklist

- [ ] Rate limiting is enabled and configured
- [ ] Input validation is active for all inputs
- [ ] Threat detection is operational
- [ ] Security events are being logged
- [ ] Domain allowlist is properly configured
- [ ] Blocked entities are actively managed
- [ ] Data sanitization is working correctly
- [ ] Security reports are being generated
- [ ] Administrator alerts are configured
- [ ] Incident response procedures are documented

### Log Retention

- **Security Events**: Retain for 90 days minimum
- **Blocked Entities**: Retain for 30 days
- **Threat Intelligence**: Retain for 180 days
- **Audit Logs**: Retain for 365 days

### Regular Security Tasks

1. **Daily**: Review security reports for new threats
2. **Weekly**: Update domain allowlist based on new services
3. **Monthly**: Review and adjust rate limiting thresholds
4. **Quarterly**: Comprehensive security audit
5. **Annually**: Review and update security policies

## Integration Examples

### Custom Security Validation

```python
from .security_manager import GLMAgentSecurityManager, SecurityLevel

class CustomService:
    def __init__(self, hass):
        self.security_manager = GLMAAgentSecurityManager(hass)

    async def process_custom_data(self, data: dict):
        # Validate all input fields
        for key, value in data.items():
            is_valid, error = self.security_manager.validate_input(
                str(value), key, 1000
            )
            if not is_valid:
                raise ValueError(f"Invalid {key}: {error}")

        # Check rate limiting
        user_id = data.get("user_id")
        if user_id:
            is_allowed, rate_info = self.security_manager.check_rate_limit(user_id)
            if not is_allowed:
                raise ValueError("Rate limit exceeded")

        # Process data securely
        return await self._process_data(data)
```

### Security Event Monitoring

```python
# Monitor for specific security events
def handle_security_event(event):
    if event.event_type == ThreatType.INJECTION:
        # High severity - immediate response
        send_alert(event)
        block_source(event.source)

    elif event.severity == SecurityLevel.CRITICAL:
        # Critical - emergency response
        emergency_shutdown()
        notify_administrators(event)
```

This comprehensive security hardening system provides robust protection for GLM Agent HA against common security threats while maintaining usability and performance. The multi-layered approach ensures that even if one security control fails, others provide backup protection.