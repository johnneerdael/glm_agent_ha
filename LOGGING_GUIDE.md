# Structured Logging Guide for GLM Agent HA

This guide covers the comprehensive structured logging system implemented in GLM Agent HA, providing enhanced debugging, monitoring, and analysis capabilities.

## Overview

The structured logging system provides:
- **Consistent Log Format**: Structured JSON logs with standardized fields
- **Contextual Information**: Automatic correlation IDs and request tracking
- **Security Filtering**: Automatic sanitization of sensitive data
- **Performance Tracking**: Built-in performance metrics and timing
- **Categorization**: Organized logs by functional areas
- **Search and Analysis**: Enhanced log searching and filtering capabilities

## Log Categories

The logging system categorizes logs into functional areas:

### System Logs (`system`)
- Integration lifecycle events (setup, teardown)
- Configuration changes
- Service registration
- General system health

### AI Agent Logs (`ai_agent`)
- AI request processing
- Model interactions
- Prompt/response handling
- Request correlation and tracking

### MCP Integration Logs (`mcp_integration`)
- MCP server connections
- Tool operations and results
- Connection status changes
- MCP-specific events

### AI Task Entity Logs (`ai_task_entity`)
- Task entity lifecycle
- Media processing
- File operations
- Entity state changes

### Performance Logs (`performance`)
- Request timing and metrics
- Resource usage monitoring
- Performance alerts
- Statistical data

### Security Logs (`security`)
- Authentication events
- Security incidents
- Access control
- Data sanitization events

### Configuration Logs (`config`)
- Configuration changes
- Parameter updates
- Validation events
- Migration activities

### API Logs (`api`)
- External API calls
- Request/response tracking
- Rate limiting
- Connection status

### Cache Logs (`cache`)
- Cache operations
- Hit/miss statistics
- Cache invalidation
- Performance optimization

### Error Logs (`error`)
- Error conditions and exceptions
- Failure analysis
- Recovery attempts
- Debugging information

## Log Levels

The system supports standard logging levels:

- **DEBUG**: Detailed diagnostic information for development
- **INFO**: General information about normal operation
- **WARNING**: Potentially harmful situations that don't prevent normal operation
- **ERROR**: Error conditions that may affect functionality
- **CRITICAL**: Serious errors that may cause the system to fail

## Structured Log Format

### Standard Log Entry Structure
```json
{
  "timestamp": "2025-01-14T10:30:00.000000Z",
  "level": "INFO",
  "category": "ai_agent",
  "logger": "glm_agent_ha",
  "message": "AI query request completed",
  "session_id": "session_1705253100000_12345",
  "correlation_id": "req_1705253150000",
  "context": {
    "user_id": "user123",
    "request_id": "query_42"
  },
  "provider": "openai",
  "duration_ms": 1245.7,
  "success": true
}
```

### Console Output Format

#### Traditional Format (when structured output is disabled)
```
2025-01-14 10:30:00 [ai_agent] [INFO] AI query request completed [req_1705253150]
```

#### Compact Structured Format (default)
```json
{"ts":"2025-01-14 10:30:00","cat":"ai_agent","lvl":"I","msg":"AI query request completed","cid":"req_1705253150","dur":"1245.7ms"}
```

## Available Logging Services

### 1. `glm_agent_ha.logging_stats`

Get comprehensive logging statistics and metrics.

**Usage:**
```yaml
service: glm_agent_ha.logging_stats
data: {}
```

**Returns:**
```json
{
  "session_id": "session_1705253100000_12345",
  "log_counts": {
    "DEBUG": 150,
    "INFO": 450,
    "WARNING": 25,
    "ERROR": 8,
    "CRITICAL": 2
  },
  "category_counts": {
    "system": 50,
    "ai_agent": 300,
    "mcp_integration": 45,
    "performance": 75,
    "security": 15,
    "error": 150
  },
  "total_logs": 635,
  "structured_output_enabled": true,
  "file_logging_enabled": true,
  "log_file_path": "/config/logs/glm_agent_ha.log"
}
```

### 2. `glm_agent_ha.logging_search`

Search through logs with advanced filtering capabilities.

**Usage:**
```yaml
service: glm_agent_ha.logging_search
data:
  query: "error"                    # Search term (optional)
  category: "ai_agent"              # Filter by category (optional)
  level: "ERROR"                    # Filter by level (optional)
  limit: 50                         # Maximum results (default: 100)
```

**Returns:**
```json
{
  "query": "error",
  "category": "ai_agent",
  "level": "ERROR",
  "limit": 50,
  "results_count": 15,
  "results": [
    {
      "timestamp": "2025-01-14T10:25:00.000000Z",
      "level": "ERROR",
      "category": "ai_agent",
      "message": "API request failed",
      "error_type": "TimeoutError",
      "correlation_id": "req_1705253100000"
    }
  ]
}
```

## Configuration

### Environment Variables

Configure the logging system with environment variables:

```bash
# Enable structured JSON output (default: true)
GLM_AGENT_STRUCTURED_LOGS=true

# Enable file logging (default: false)
GLM_AGENT_FILE_LOGS=true

# Log file path (required if file logging enabled)
GLM_AGENT_LOG_FILE=/config/logs/glm_agent_ha.log

# Maximum log file size before rotation (default: 10MB)
GLM_AGENT_MAX_LOG_SIZE=10485760

# Enable colored console output (default: true)
GLM_AGENT_COLOR_LOGS=true
```

### Home Assistant Configuration

Add to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.glm_agent_ha: debug  # Enable debug logging for the integration
```

## Specialized Logging Methods

### API Request Logging
```python
# In your code
structured_logger.api_request(
    method="POST",
    url="https://api.openai.com/v1/chat/completions",
    status_code=200,
    duration_ms=1234.5
)
```

### AI Request Logging
```python
structured_logger.ai_request(
    request_type="query",
    provider="openai",
    model="GLM-4.6",
    tokens_used=150,
    duration_ms=2345.6,
    success=True
)
```

### MCP Operation Logging
```python
structured_logger.mcp_operation(
    operation="tool_call",
    server="filesystem",
    success=True,
    duration_ms=123.4
)
```

### Performance Metric Logging
```python
structured_logger.performance_metric(
    metric_name="memory_usage",
    value=256.7,
    unit="MB"
)
```

### Security Event Logging
```python
structured_logger.security_event(
    event_type="api_key_validation",
    severity="info",
    details={"provider": "openai", "status": "valid"}
)
```

### Configuration Change Logging
```python
structured_logger.config_change(
    component="ai_agent",
    change_type="model_update",
    old_value="GLM-4.5",
    new_value="GLM-4.6"
)
```

## Context Management

### Request Context
Track requests across multiple log entries:

```python
from .structured_logger import RequestContext

# Use context manager for request tracking
async def process_request(request_data):
    correlation_id = f"req_{int(time.time() * 1000)}"

    with RequestContext(structured_logger, correlation_id,
                       user_id=request_data.get("user_id"),
                       request_type=request_data.get("type")):
        # All logs within this context will include the correlation_id and context
        structured_logger.info("Processing request started")

        # Your processing logic here
        result = await do_something()

        structured_logger.info("Processing request completed",
                             result_type=type(result).__name__)
```

### Manual Context Management
```python
# Set correlation ID manually
structured_logger.set_correlation_id("custom_correlation_123")

# Add context information
structured_logger.set_request_context({
    "user_id": "user123",
    "session_id": "session_456",
    "operation": "dashboard_generation"
})

# Clear context when done
structured_logger.clear_request_context()
```

## Security Features

### Automatic Data Sanitization
The logging system automatically detects and sanitizes sensitive data:

- **API Keys**: Replaced with `***REDACTED***`
- **Tokens**: Replaced with `***REDACTED***`
- **Passwords**: Replaced with `***REDACTED***`
- **Secrets**: Replaced with `***REDACTED***`

### Sensitive Key Detection
The system looks for these patterns in keys and values:
- `token`, `key`, `password`, `secret`, `credential`, `auth`
- `openai_token`, `api_key`, `access_token`, `refresh_token`

### Manual Sanitization
```python
# The system automatically sanitizes sensitive data
structured_logger.info("Configuration loaded", LogCategory.CONFIG,
                       openai_token="sk-actual-secret-key",  # Will be redacted
                       model="GLM-4.6")  # Will be logged normally
```

## Performance Monitoring

### Built-in Performance Tracking
The logging system tracks:
- **Log Counts**: Count of logs by level and category
- **Session Metrics**: Statistics for current session
- **File Rotation**: Automatic log file rotation when size limits reached

### Performance Logging
```python
# Use the performance decorator
@log_performance(structured_logger, "database_query")
async def execute_query(sql):
    # Function execution will be automatically timed
    return await database.execute(sql)

# Manual performance logging
structured_logger.performance_metric(
    metric_name="query_duration",
    value=45.2,
    unit="ms",
    query_type="SELECT"
)
```

## Log Analysis and Monitoring

### Log Patterns to Monitor

#### High Error Rates
```yaml
# Automation to alert on high error rates
alias: GLM Agent HA High Error Rate
trigger:
  - platform: template
    value_template: >-
      {{ state_attr('sensor.glm_agent_ha_logging_stats', 'log_counts').ERROR > 10 }}
action:
  - service: notify.persistent_notification
    data:
      title: "GLM Agent HA High Error Rate"
      message: >-
        Error count: {{ state_attr('sensor.glm_agent_ha_logging_stats', 'log_counts').ERROR }}
        Consider checking system health and API connectivity
```

#### Security Events
```yaml
# Monitor security events
alias: GLM Agent HA Security Alert
trigger:
  - platform: event
    event_type: glm_agent_ha_security_event
action:
  - service: notify.persistent_notification
    data:
      title: "GLM Agent HA Security Event"
      message: >-
        Event: {{ trigger.event.data.event_type }}
        Severity: {{ trigger.event.data.severity }}
        Time: {{ trigger.event.data.timestamp }}
```

### Log Aggregation
For advanced monitoring, integrate with external systems:

#### ELK Stack Integration
```yaml
# Filebeat configuration for GLM Agent HA logs
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /config/logs/glm_agent_ha.log
  json.keys_under_root: true
  json.add_error_key: true

  processors:
    - timestamp:
        field: timestamp
        layouts:
          - '2006-01-02T15:04:05.999Z'
        test:
          - '2024-01-14T10:30:00.000000Z'
```

#### Prometheus Integration
```python
# Export log metrics to Prometheus
from prometheus_client import Counter, Histogram

log_counter = Counter('glm_agent_ha_logs_total', 'Total logs', ['level', 'category'])
request_duration = Histogram('glm_agent_ha_request_duration_seconds', 'Request duration')

# In your logging code
structured_logger.info("Request processed")
log_counter.labels(level='INFO', category='ai_agent').inc()
request_duration.observe(duration_ms / 1000)
```

## Troubleshooting

### Common Issues

#### Logs Not Appearing
1. Check log level configuration
2. Verify structured logger initialization
3. Check file permissions for log file
4. Review Home Assistant log configuration

#### Structured Output Not Working
1. Verify `GLM_AGENT_STRUCTURED_LOGS=true`
2. Check console output configuration
3. Restart Home Assistant after changing environment variables

#### File Logging Issues
1. Ensure log directory exists and is writable
2. Check disk space availability
3. Verify log file path is correct
4. Check file permissions

#### Performance Impact
1. Monitor log file sizes and rotation
2. Adjust log levels to reduce verbosity
3. Use structured output for better parsing performance
4. Consider log aggregation for high-volume scenarios

### Debug Information

Enable comprehensive debugging:

```yaml
# In configuration.yaml
logger:
  default: debug
  logs:
    custom_components.glm_agent_ha: debug
    homeassistant.core: debug
```

```bash
# Set environment variables
export GLM_AGENT_STRUCTURED_LOGS=true
export GLM_AGENT_FILE_LOGS=true
export GLM_AGENT_COLOR_LOGS=true
```

## Best Practices

### Log Level Usage
- **DEBUG**: Detailed development information, avoid in production
- **INFO**: Normal operational information, use for significant events
- **WARNING**: Potentially problematic situations that don't stop operation
- **ERROR**: Error conditions that affect functionality
- **CRITICAL**: Serious errors that may cause system failure

### Message Formatting
- Use clear, descriptive messages
- Include relevant context in structured fields
- Avoid sensitive information in messages
- Use consistent terminology

### Performance Considerations
- Use appropriate log levels to minimize noise
- Leverage structured logging for efficient parsing
- Implement log rotation to manage disk usage
- Consider asynchronous logging for high-volume scenarios

### Security Practices
- Never log sensitive credentials or tokens
- Use the built-in sanitization features
- Review logs before sharing for troubleshooting
- Implement log access controls in production

## Integration Examples

### Custom Component Integration
```python
from .structured_logger import get_logger, LogCategory

class MyCustomComponent:
    def __init__(self, hass):
        self.logger = get_logger(hass, "my_component")
        self.logger.info("Custom component initialized", LogCategory.SYSTEM)

    async def process_data(self, data):
        with RequestContext(self.logger, f"process_{int(time.time())}"):
            self.logger.info("Starting data processing", LogCategory.SYSTEM,
                           data_size=len(data))

            try:
                result = await self.do_processing(data)
                self.logger.info("Data processing completed", LogCategory.SYSTEM,
                               result_count=len(result))
                return result
            except Exception as e:
                self.logger.error("Data processing failed", LogCategory.ERROR,
                                error_type=type(e).__name__, exc_info=True)
                raise
```

### Automation Integration
```yaml
# Log automation execution
alias: GLM Agent HA Automation Execution
trigger:
  - platform: event
    event_type: automation_triggered
action:
  - service: glm_agent_ha.logging_info
    data:
      message: "Automation executed"
      category: "system"
      automation_id: "{{ trigger.event.data.automation_id }}"
      trigger_type: "{{ trigger.event.data.trigger_type }}"
```

This comprehensive structured logging system provides powerful debugging and monitoring capabilities for GLM Agent HA, making it easier to troubleshoot issues, track performance, and maintain system health.