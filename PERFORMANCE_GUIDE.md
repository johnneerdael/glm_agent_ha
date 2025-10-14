# Performance Monitoring Guide for GLM Agent HA

This guide covers the comprehensive performance monitoring system built into GLM Agent HA, which tracks AI request patterns, identifies bottlenecks, and provides insights for optimization.

## Overview

The performance monitoring system provides:
- Real-time request tracking with timing and success metrics
- Historical performance data and trend analysis
- Automatic performance alerting for issues
- Export capabilities for external analysis
- Integration with Home Assistant's automation system

## Available Performance Services

### 1. `glm_agent_ha.performance_current`

Get real-time performance metrics including current request rates, success rates, and system resource usage.

**Usage:**
```yaml
service: glm_agent_ha.performance_current
data: {}
```

**Returns:**
```json
{
  "timestamp": "2025-01-14T10:30:00.000000",
  "total_requests": 150,
  "active_requests": 2,
  "requests_per_minute": 3.2,
  "success_rate": 96.5,
  "average_duration_ms": 1245.7,
  "cache_hit_rate": 15.2,
  "total_input_tokens": 45678,
  "total_output_tokens": 12345,
  "current_session": true,
  "memory_usage_mb": 256.3
}
```

### 2. `glm_agent_ha.performance_aggregated`

Get aggregated performance metrics over a specified time period.

**Usage:**
```yaml
service: glm_agent_ha.performance_aggregated
data:
  period_hours: 24  # Optional: default is 24 hours
```

**Returns:**
```json
{
  "period_start": "2025-01-13T10:30:00.000000",
  "period_end": "2025-01-14T10:30:00.000000",
  "total_requests": 1250,
  "successful_requests": 1205,
  "failed_requests": 45,
  "average_duration_ms": 1356.2,
  "median_duration_ms": 1123.4,
  "p95_duration_ms": 2856.7,
  "p99_duration_ms": 4523.1,
  "min_duration_ms": 234.5,
  "max_duration_ms": 6789.2,
  "total_input_tokens": 234567,
  "total_output_tokens": 67890,
  "cache_hit_rate": 12.3,
  "error_rate": 3.6,
  "requests_by_type": {
    "query": 1100,
    "automation": 100,
    "dashboard": 50
  },
  "requests_by_provider": {
    "openai": 1250
  },
  "requests_by_model": {
    "GLM-4.6": 1250
  },
  "top_errors": [
    {"error_type": "TimeoutError", "count": 20},
    {"error_type": "RateLimitError", "count": 15},
    {"error_type": "ConnectionError", "count": 10}
  ]
}
```

### 3. `glm_agent_ha.performance_trends`

Get performance trends over multiple days to identify patterns and changes.

**Usage:**
```yaml
service: glm_agent_ha.performance_trends
data:
  days: 7  # Optional: default is 7 days
```

**Returns:**
```json
{
  "period_days": 7,
  "daily_data": [
    {
      "date": "2025-01-14",
      "total_requests": 180,
      "success_rate": 95.5,
      "average_duration_ms": 1298.3,
      "cache_hit_rate": 14.2
    },
    {
      "date": "2025-01-13",
      "total_requests": 165,
      "success_rate": 97.1,
      "average_duration_ms": 1187.6,
      "cache_hit_rate": 16.8
    }
  ],
  "request_volume_trend_percent": 9.1,
  "success_rate_trend_percent": -1.6,
  "analysis_date": "2025-01-14T10:30:00.000000"
}
```

### 4. `glm_agent_ha.performance_slow_requests`

Get the slowest recent requests for performance analysis.

**Usage:**
```yaml
service: glm_agent_ha.performance_slow_requests
data:
  limit: 10  # Optional: default is 10 requests
```

**Returns:**
```json
[
  {
    "timestamp": "2025-01-14T10:25:00.000000",
    "request_id": "query_1705253100000",
    "request_type": "query",
    "provider": "openai",
    "model": "GLM-4.6",
    "duration_ms": 6789.2,
    "success": true,
    "error_type": null,
    "prompt_length": 1250,
    "response_length": 3456,
    "input_tokens": 312,
    "output_tokens": 864
  }
]
```

### 5. `glm_agent_ha.performance_export`

Export performance data for external analysis in JSON or CSV format.

**Usage:**
```yaml
service: glm_agent_ha.performance_export
data:
  format: "json"  # Optional: "json" or "csv", default is "json"
```

**Returns:**
```json
{
  "export_data": "{... comprehensive performance data ...}",
  "format": "json",
  "timestamp": "2025-01-14T10:30:00.000000"
}
```

### 6. `glm_agent_ha.performance_reset`

Reset all performance metrics and start fresh monitoring.

**Usage:**
```yaml
service: glm_agent_ha.performance_reset
data: {}
```

**Returns:**
```json
{
  "message": "Performance metrics reset successfully"
}
```

## Performance Metrics Explained

### Request Metrics

- **Total Requests**: Count of all processed requests
- **Successful Requests**: Count of successfully completed requests
- **Failed Requests**: Count of failed requests
- **Success Rate**: Percentage of successful requests
- **Error Rate**: Percentage of failed requests

### Timing Metrics

- **Duration (ms)**: Time taken to complete requests
- **Average Duration**: Mean of all request durations
- **Median Duration**: Middle value of all request durations
- **P95 Duration**: 95th percentile of request durations
- **P99 Duration**: 99th percentile of request durations
- **Min/Max Duration**: Fastest and slowest request times

### Token Metrics

- **Input Tokens**: Total tokens sent to AI models
- **Output Tokens**: Total tokens received from AI models
- **Cache Hit Rate**: Percentage of requests served from cache

### System Metrics

- **Memory Usage (MB)**: Estimated memory usage by the monitoring system
- **Active Requests**: Number of currently processing requests
- **Requests per Minute**: Current request rate

## Performance Alerts

The monitoring system automatically generates alerts for:

### Slow Requests
Alerts are fired when individual requests take longer than 5 seconds:
```json
{
  "type": "slow_request",
  "severity": "warning",
  "message": "Slow query request: 5234.5ms",
  "request_id": "query_1705253100000",
  "threshold_ms": 5000
}
```

### High Memory Usage
Alerts are fired when estimated memory usage exceeds 1GB:
```json
{
  "type": "high_memory_usage",
  "severity": "warning",
  "message": "High memory usage: 1024.5MB",
  "usage_mb": 1024.5,
  "threshold_mb": 1000
}
```

### High Error Rate
Alerts are fired when the error rate exceeds 10% over a recent period:
```json
{
  "type": "high_error_rate",
  "severity": "warning",
  "message": "High error rate: 12.5%",
  "error_rate": 12.5,
  "threshold_percent": 10
}
```

## Automation Examples

### Performance Health Monitor

Create an automation to monitor performance and send notifications:

```yaml
alias: GLM Agent HA Performance Monitor
description: Monitor GLM Agent HA performance and alert on issues
trigger:
  - platform: time_pattern
    minutes: "/10"  # Every 10 minutes
condition: []
action:
  - service: glm_agent_ha.performance_current
    response_variable: current_metrics
  - choose:
      - conditions:
          - condition: template
            value_template: >-
              {{ current_metrics.success_rate < 90 }}
        sequence:
          - service: notify.persistent_notification
            data:
              title: "GLM Agent HA Performance Alert"
              message: >-
                GLM Agent HA success rate dropped to {{ current_metrics.success_rate }}%
                Average response time: {{ current_metrics.average_duration_ms }}ms
              data:
                tag: "glm_agent_ha_performance"
      - conditions:
          - condition: template
            value_template: >-
              {{ current_metrics.average_duration_ms > 3000 }}
        sequence:
          - service: notify.persistent_notification
            data:
              title: "GLM Agent HA Slow Response"
              message: >-
                GLM Agent HA average response time is {{ current_metrics.average_duration_ms }}ms
                Consider checking network connectivity or API status
              data:
                tag: "glm_agent_ha_performance"
```

### Performance Trends Dashboard

Create sensors to track performance trends:

```yaml
template:
  - sensor:
      - name: "GLM Agent HA Success Rate"
        unit_of_measurement: "%"
        state: >-
          {{ state_attr('sensor.glm_agent_ha_performance_current', 'success_rate') }}
        icon: "mdi:check-circle"
      - sensor:
      - name: "GLM Agent HA Average Response Time"
        unit_of_measurement: "ms"
        state: >-
          {{ state_attr('sensor.glm_agent_ha_performance_current', 'average_duration_ms') }}
        icon: "mdi:clock"
      - sensor:
      - name: "GLM Agent HA Request Rate"
        unit_of_measurement: "req/min"
        state: >-
          {{ state_attr('sensor.glm_agent_ha_performance_current', 'requests_per_minute') }}
        icon: "mdi:chart-line"
```

### Daily Performance Report

Create an automation for daily performance reports:

```yaml
alias: GLM Agent HA Daily Performance Report
description: Generate daily performance report
trigger:
  - platform: time
    at: "23:59:00"
condition: []
action:
  - service: glm_agent_ha.performance_aggregated
    data:
      period_hours: 24
    response_variable: daily_metrics
  - service: glm_agent_ha.performance_trends
    data:
      days: 7
    response_variable: weekly_trends
  - service: notify.persistent_notification
    data:
      title: "GLM Agent HA Daily Performance Report"
      message: >-
        **Daily Summary:**
        Total Requests: {{ daily_metrics.total_requests }}
        Success Rate: {{ daily_metrics.success_rate }}%
        Average Response: {{ daily_metrics.average_duration_ms }}ms
        Cache Hit Rate: {{ daily_metrics.cache_hit_rate }}%

        **Weekly Trend:**
        Request Volume: {{ weekly_trends.request_volume_trend_percent }}%
        Success Rate: {{ weekly_trends.success_rate_trend_percent }}%

        **Top Issues:**
        {% for error in daily_metrics.top_errors[:3] %}
        - {{ error.error_type }}: {{ error.count }} times
        {% endfor %}
      data:
        tag: "glm_agent_ha_daily_report"
```

## Performance Optimization

### Analyzing Slow Requests

Use the slow requests service to identify performance bottlenecks:

```yaml
service: glm_agent_ha.performance_slow_requests
data:
  limit: 5
```

Look for patterns in slow requests:
- **Request Type**: Certain types (complex queries, dashboard generation) may be inherently slower
- **Prompt Length**: Longer prompts generally take longer to process
- **Response Length**: Very long responses may indicate inefficient prompts
- **Time of Day**: Performance may vary based on API provider load

### Cache Optimization

Monitor cache hit rates to improve performance:

```yaml
# Low cache hit rate automation
alias: GLM Agent HA Low Cache Hit Rate
trigger:
  - platform: template
    value_template: >-
      {{ state_attr('sensor.glm_agent_ha_performance_current', 'cache_hit_rate') < 10 }}
action:
  - service: notify.persistent_notification
    data:
      title: "GLM Agent HA Low Cache Hit Rate"
      message: >-
        Cache hit rate is {{ state_attr('sensor.glm_agent_ha_performance_current', 'cache_hit_rate') }}%
        Consider enabling more caching or reviewing query patterns for optimization
```

### Token Usage Optimization

Track token usage to control costs:

```yaml
# High token usage alert
alias: GLM Agent HA High Token Usage
trigger:
  - platform: template
    value_template: >-
      {{ state_attr('sensor.glm_agent_ha_performance_current', 'total_input_tokens') > 100000 }}
action:
  - service: notify.persistent_notification
    data:
      title: "GLM Agent HA High Token Usage"
      message: >-
        Input tokens consumed: {{ state_attr('sensor.glm_agent_ha_performance_current', 'total_input_tokens') }}
        Consider optimizing prompts or implementing rate limiting
```

## Data Export and Analysis

### Exporting Performance Data

Export data for external analysis:

```yaml
# Export to JSON for analysis
service: glm_agent_ha.performance_export
data:
  format: "json"
```

```yaml
# Export to CSV for spreadsheet analysis
service: glm_agent_ha.performance_export
data:
  format: "csv"
```

### External Analysis Tools

The exported data can be analyzed with:
- **Excel/Google Sheets**: For CSV exports and trend analysis
- **Grafana**: For creating dashboards with time series data
- **Python/Pandas**: For advanced statistical analysis
- **Prometheus/Grafana**: For integration with existing monitoring infrastructure

## Performance Tuning

### Request Optimization

1. **Prompt Engineering**: Optimize prompts for clarity and conciseness
2. **Batch Processing**: Group similar requests when possible
3. **Caching**: Enable caching for frequently repeated queries
4. **Model Selection**: Choose appropriate models based on task complexity

### System Optimization

1. **Memory Management**: Monitor memory usage and reset metrics periodically
2. **Rate Limiting**: Implement appropriate rate limits to prevent API throttling
3. **Error Handling**: Implement robust error handling with appropriate retries
4. **Network Optimization**: Ensure stable network connectivity to API providers

### Monitoring Best Practices

1. **Regular Reviews**: Schedule regular performance reviews
2. **Alert Tuning**: Adjust alert thresholds based on normal usage patterns
3. **Data Retention**: Balance data retention with storage constraints
4. **Integration**: Integrate with existing monitoring and alerting systems

## Troubleshooting Performance Issues

### High Response Times

1. Check network connectivity to API providers
2. Verify API provider status and performance
3. Review recent changes in prompts or configuration
4. Check for system resource constraints

### High Error Rates

1. Review API key configuration and permissions
2. Check rate limits and quotas
3. Verify model availability and compatibility
4. Review error types in aggregated metrics

### Memory Issues

1. Reset performance metrics periodically
2. Check for memory leaks in long-running processes
3. Monitor Home Assistant system resources
4. Consider adjusting history retention settings

## Integration with Other Systems

### Home Assistant Energy Dashboard

Track AI request costs alongside energy usage:

```yaml
sensor:
  - platform: template
    sensors:
      glm_agent_ha_daily_cost:
        unit_of_measurement: "$"
        state_class: total_increasing
        value_template: >-
          {% set tokens = state_attr('sensor.glm_agent_ha_performance_current', 'total_input_tokens') %}
          {% set cost_per_token = 0.00001 %}
          {{ (tokens * cost_per_token) | round(4) }}
```

### Node-RED Integration

Send performance data to Node-RED for advanced processing:

```yaml
automation:
  - alias: "Send Performance to Node-RED"
    trigger:
      - platform: time_pattern
        minutes: 5
    action:
      - service: glm_agent_ha.performance_current
        response_variable: metrics
      - service: rest_command.glm_performance_to_nodered
        data:
          metrics: "{{ metrics | tojson }}"
```

This comprehensive performance monitoring system provides deep insights into GLM Agent HA's operation and helps maintain optimal performance for your AI-powered home automation.