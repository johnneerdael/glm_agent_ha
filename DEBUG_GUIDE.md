# Debugging Services for GLM Agent HA

This document describes the comprehensive debugging services available for troubleshooting GLM Agent HA integration issues.

## Available Debug Services

### 1. `glm_agent_ha.debug_info`

Get detailed integration status including AI agent, MCP integration, and AI Task entity status.

**Usage:**
```yaml
service: glm_agent_ha.debug_info
data:
  entry_id: "optional-specific-config-entry-id"
```

**Returns:**
```json
{
  "timestamp": "2025-01-14T10:30:00.000000",
  "integration_status": "configured",
  "config_entry": {
    "entry_id": "abc123...",
    "title": "GLM Agent HA",
    "plan": "pro",
    "provider": "openai"
  },
  "ai_agent": {
    "initialized": true,
    "provider": "openai",
    "api_key_configured": true,
    "model_configuration": {...}
  },
  "mcp_integration": {
    "available": true,
    "servers_status": {...},
    "connection_test": {
      "success": true,
      "attempted_at": "2025-01-14T10:30:00.000000"
    }
  },
  "ai_task_entity": {
    "available": true,
    "status": "ready"
  }
}
```

### 2. `glm_agent_ha.debug_system`

Get comprehensive system information including memory, disk space, network connectivity, and environment variables.

**Usage:**
```yaml
service: glm_agent_ha.debug_system
data: {}
```

**Returns:**
```json
{
  "timestamp": "2025-01-14T10:30:00.000000",
  "python_version": "3.12.0",
  "platform": "Linux-6.1.0-x86_64",
  "architecture": "x86_64",
  "homeassistant_version": "2025.1.0",
  "environment_variables": {
    "Z_AI_API_KEY": "configured",
    "CONTEXT7_API_KEY": "configured",
    "JINA_API_KEY": "missing",
    ...
  },
  "available_memory": {
    "total": 8589934592,
    "available": 4294967296,
    "used": 4294967296,
    "percent": 50.0,
    "available_mb": 4096.0,
    "used_mb": 4096.0
  },
  "disk_space": {
    "total_gb": 100.0,
    "available_gb": 50.0,
    "used_gb": 50.0,
    "usage_percent": 50.0
  },
  "network_connectivity": {
    "google_dns": {
      "success": true,
      "response_time_ms": 15.5,
      "host": "8.8.8.8",
      "port": 53
    },
    "zai_api": {
      "success": true,
      "response_time_ms": 125.3,
      "host": "api.z.ai",
      "port": 443
    }
  }
}
```

### 3. `glm_agent_ha.debug_api`

Test API connections to external services with response time monitoring.

**Usage:**
```yaml
service: glm_agent_ha.debug_api
data:
  entry_id: "optional-specific-config-entry-id"
```

**Returns:**
```json
{
  "timestamp": "2025-01-14T10:30:00.000000",
  "tests": {
    "openai_api": {
      "success": true,
      "status_code": 200,
      "response_time_ms": 245.7,
      "test_url": "https://api.openai.com/v1/models"
    },
    "zai_api": {
      "success": true,
      "status_code": 400,
      "response_time_ms": 189.2,
      "test_url": "https://api.z.ai/api/v1/analyze_image"
    }
  }
}
```

### 4. `glm_agent_ha.debug_logs`

Get recent service logs for troubleshooting.

**Usage:**
```yaml
service: glm_agent_ha.debug_logs
data:
  entry_id: "optional-specific-config-entry-id"
  lines: 100  # Optional: number of lines to retrieve (default: 100)
```

**Returns:**
```json
{
  "timestamp": "2025-01-14T10:30:00.000000",
  "total_log_lines": 25,
  "recent_logs": [
    "2025-01-14 10:29:45 DEBUG (MainThread) [custom_components.glm_agent_ha.agent] Processing query...",
    "2025-01-14 10:29:46 INFO (MainThread) [custom_components.glm_agent_ha.agent] AI response received",
    ...
  ],
  "log_level": "debug"
}
```

### 5. `glm_agent_ha.debug_report`

Generate comprehensive debug report including all debugging information and recommendations.

**Usage:**
```yaml
service: glm_agent_ha.debug_report
data:
  entry_id: "optional-specific-config-entry-id"
```

**Returns:**
```json
{
  "report_timestamp": "2025-01-14T10:30:00.000000",
  "report_version": "1.0.0",
  "glm_agent_ha_debug_report": true,
  "system_info": {...},
  "integration_status": {...},
  "api_connections": {...},
  "recent_logs": {...},
  "recommendations": [
    "✅ All systems appear to be functioning correctly",
    "⚠️ Missing environment variables: JINA_API_KEY, TAVILY_API_KEY",
    "ℹ️ Disk usage is 85% - consider cleaning up files"
  ]
}
```

## Common Troubleshooting Workflows

### Config Flow Issues

If you're experiencing "Invalid handler specified" errors in the config flow:

1. **Check integration status:**
   ```yaml
   service: glm_agent_ha.debug_info
   ```

2. **Check system info for missing dependencies:**
   ```yaml
   service: glm_agent_ha.debug_system
   ```

3. **Generate full report:**
   ```yaml
   service: glm_agent_ha.debug_report
   ```

### API Connection Issues

If AI requests are failing:

1. **Test API connections:**
   ```yaml
   service: glm_agent_ha.debug_api
   ```

2. **Check environment variables:**
   ```yaml
   service: glm_agent_ha.debug_system
   ```
   Look for missing API keys in the `environment_variables` section.

3. **Check recent logs:**
   ```yaml
   service: glm_agent_ha.debug_logs
   data:
     lines: 200
   ```

### MCP Integration Issues

If MCP features aren't working:

1. **Check integration status:**
   ```yaml
   service: glm_agent_ha.debug_info
   ```
   Look at the `mcp_integration` section.

2. **Test network connectivity:**
   ```yaml
   service: glm_agent_ha.debug_system
   ```
   Check the `network_connectivity` section.

3. **Generate comprehensive report:**
   ```yaml
   service: glm_agent_ha.debug_report
   ```

### Performance Issues

If the integration is slow or unresponsive:

1. **Check system resources:**
   ```yaml
   service: glm_agent_ha.debug_system
   ```
   Monitor `available_memory` and `disk_space` usage percentages.

2. **Test API response times:**
   ```yaml
   service: glm_agent_ha.debug_api
   ```
   Look for high `response_time_ms` values.

3. **Check for errors in logs:**
   ```yaml
   service: glm_agent_ha.debug_logs
   data:
     lines: 500
   ```

## Automation Examples

### Automated Health Check

Create an automation to periodically check integration health:

```yaml
alias: GLM Agent HA Health Check
description: Weekly health check for GLM Agent HA
trigger:
  - platform: time
    at: "02:00:00"
condition: []
action:
  - service: glm_agent_ha.debug_report
    response_variable: debug_report
  - choose:
      - conditions:
          - condition: template
            value_template: >-
              {{ debug_report.recommendations | select('search', '⚠️') | list | length > 0 }}
        sequence:
          - service: notify.persistent_notification
            data:
              title: "GLM Agent HA Health Warning"
              message: >-
                GLM Agent HA health check found issues:
                {{ debug_report.recommendations | join('\n') }}
              data:
                tag: "glm_agent_ha_health"
    default:
      - service: persistent_notification.create
        data:
          title: "GLM Agent HA Health Check"
          message: "✅ All systems functioning correctly"
          notification_id: "glm_agent_ha_health"
mode: single
```

### API Failure Alert

Get notified when API connections fail:

```yaml
alias: GLM Agent HA API Failure Alert
description: Alert when API connections fail
trigger:
  - platform: event
    event_type: call_service
    event_data:
      domain: glm_agent_ha
      service: debug_api
condition:
  - condition: template
    value_template: >-
      {{ trigger.event.data.response_variable.tests | dictselect('success', false) | list | length > 0 }}
action:
  - service: notify.persistent_notification
    data:
      title: "GLM Agent HA API Failure"
      message: >-
        The following API connections failed:
        {% for service, result in trigger.event.data.response_variable.tests.items() %}
        {% if not result.success %}
        - {{ service }}: {{ result.error | default('Unknown error') }}
        {% endif %}
        {% endfor %}
      data:
        tag: "glm_agent_ha_api_failure"
mode: single
```

## Script Development

### Custom Debug Script

Create a script to run comprehensive diagnostics:

```yaml
alias: GLM Agent HA Full Diagnostics
sequence:
  - service: glm_agent_ha.debug_system
    response_variable: system_info
  - service: glm_agent_ha.debug_info
    response_variable: integration_status
  - service: glm_agent_ha.debug_api
    response_variable: api_tests
  - service: glm_agent_ha.debug_logs
    data:
      lines: 50
    response_variable: recent_logs
  - service: persistent_notification.create
    data:
      title: "GLM Agent HA Diagnostics Complete"
      message: >-
        System Status: {{ system_info.platform }} - {{ system_info.available_memory.percent }}% memory used

        Integration Status: {{ integration_status.integration_status }}

        API Tests: {{ api_tests.tests | dictselect('success', true) | list | length }}/{{ api_tests.tests | length }} successful

        Recent Logs: {{ recent_logs.total_log_lines }} entries found
      notification_id: "glm_agent_ha_diagnostics"
mode: single
```

## Data Interpretation

### Status Indicators

- **✅ Success**: Everything is working correctly
- **⚠️ Warning**: Non-critical issue that should be addressed
- **❌ Error**: Critical issue requiring immediate attention
- **ℹ️ Info**: Informational message or suggestion

### Memory Usage

- **< 70%**: Healthy
- **70-85%**: Monitor closely
- **> 85%**: Critical - consider cleanup or upgrade

### Disk Usage

- **< 80%**: Healthy
- **80-90%**: Warning - cleanup recommended
- **> 90%**: Critical - immediate cleanup required

### API Response Times

- **< 500ms**: Excellent
- **500ms-2s**: Good
- **2s-5s**: Slow - monitor for degradation
- **> 5s**: Critical - network or service issue

## Integration with Monitoring Tools

### Prometheus Metrics

You can create sensors to track debugging metrics:

```yaml
template:
  - sensor:
      - name: "GLM Agent HA Memory Usage"
        unit_of_measurement: "%"
        state: >-
          {{ state_attr('sensor.glm_agent_ha_debug_system', 'available_memory').percent }}
      - name: "GLM Agent HA Disk Usage"
        unit_of_measurement: "%"
        state: >-
          {{ state_attr('sensor.glm_agent_ha_debug_system', 'disk_space').usage_percent }}
      - name: "GLM Agent HA API Response Time"
        unit_of_measurement: "ms"
        state: >-
          {{ state_attr('sensor.glm_agent_ha_debug_api', 'tests').openai_api.response_time_ms }}
```

## Troubleshooting Common Issues

### Environment Variables Not Found

If you see "missing" for API keys:

1. Check your `.env` file or system environment variables
2. Ensure variables are set before starting Home Assistant
3. Restart Home Assistant after setting variables
4. Use the `debug_system` service to verify configuration

### MCP Connection Failures

If MCP integration shows errors:

1. Check network connectivity to required services
2. Verify API keys are correctly configured
3. Check if required MCP servers are running
4. Review recent logs for specific error messages

### AI Task Entity Issues

If AI Task entity fails to initialize:

1. Check `www` directory permissions
2. Ensure media directory exists and is writable
3. Verify Home Assistant has file system access
4. Check for recent configuration changes

## Best Practices

1. **Regular Monitoring**: Schedule periodic health checks using the debug services
2. **Log Management**: Keep an eye on log file sizes and rotate if necessary
3. **Performance Tracking**: Monitor API response times and system resource usage
4. **Security**: Never expose debug reports publicly as they contain sensitive configuration information
5. **Documentation**: Keep records of debug reports for trend analysis and troubleshooting history

## Getting Help

When seeking support for GLM Agent HA issues:

1. Run `glm_agent_ha.debug_report` to gather comprehensive information
2. Sanitize the report by removing sensitive API keys and personal information
3. Include the debug report in your support request
4. Provide specific error messages and reproduction steps
5. Document recent changes to your Home Assistant configuration

The debug services provide powerful visibility into the integration's operation and are essential for maintaining a healthy GLM Agent HA installation.