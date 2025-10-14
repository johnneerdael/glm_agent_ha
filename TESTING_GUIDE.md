# Comprehensive Testing Guide for GLM Agent HA

This guide covers the complete testing framework implemented for GLM Agent HA, including unit tests, integration tests, security tests, and performance tests.

## Overview

The testing suite provides comprehensive coverage of:
- **Integration Setup**: Config flow, service registration, and initialization
- **Agent Services**: Core AI query, automation, and dashboard services
- **Security System**: Input validation, rate limiting, threat detection
- **Performance Monitoring**: Metrics collection, alerting, and health checks
- **Debugging System**: Logging, error handling, and diagnostics
- **MCP Integration**: Model Context Protocol functionality and error recovery

## Test Structure

```
tests/
├── conftest.py                 # Test fixtures and configuration
├── pytest.ini                 # Pytest configuration
├── test_integration_setup.py   # Integration setup tests
├── test_agent_services.py      # AI agent service tests
├── test_security_system.py     # Security system tests
├── test_performance_monitoring.py  # Performance monitoring tests
├── test_debugging_system.py    # Debugging and logging tests
└── test_mcp_integration.py     # MCP integration tests
```

## Running Tests

### Prerequisites

Install test dependencies:

```bash
pip install -r requirements-dev.txt
```

### Basic Test Execution

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=custom_components/glm_agent_ha --cov-report=html

# Run specific test categories
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m security      # Security tests only
pytest -m performance   # Performance tests only
pytest -m mcp          # MCP tests only
```

### Test Configuration

The `pytest.ini` file configures:
- Test discovery patterns
- Coverage reporting
- Markers for test categorization
- Warning filters

### Coverage Requirements

- **Minimum Coverage**: 80%
- **Target Coverage**: 90%+
- **Coverage Reports**: HTML, XML, and terminal

## Test Categories

### 1. Integration Setup Tests (`test_integration_setup.py`)

Tests the core integration setup and configuration flow:

**Key Test Areas:**
- Config entry setup and teardown
- Configuration flow validation
- API key validation
- Service registration
- Error handling during setup

**Example Test:**
```python
async def test_async_setup_entry_success(self, hass, mock_config_entry):
    """Test successful setup of config entry."""
    with patch("custom_components.glm_agent_ha.async_setup_entry", return_value=True):
        result = await async_setup_entry(hass, mock_config_entry)
        assert result
```

### 2. Agent Services Tests (`test_agent_services.py`)

Tests all AI agent service functionality:

**Key Test Areas:**
- Query service with different inputs
- Automation creation and validation
- Dashboard generation
- Conversation history management
- Error handling and recovery
- Rate limiting integration
- Performance tracking

**Example Test:**
```python
async def test_query_service_basic(self, hass_with_config, mock_openai_client):
    """Test basic query service functionality."""
    with patch.object(hass.data[DOMAIN], "agent") as mock_agent:
        mock_agent.async_query = AsyncMock(return_value={
            "response": "Test response",
            "model": "gpt-4",
            "tokens_used": 15
        })

        await hass.services.async_call(DOMAIN, "query", {"prompt": "Hello"}, blocking=True)
        mock_agent.async_query.assert_called_once()
```

### 3. Security System Tests (`test_security_system.py`)

Comprehensive security testing:

**Key Test Areas:**
- Input validation (SQL injection, XSS, path traversal)
- Rate limiting functionality
- Threat detection and anomaly identification
- Domain allowlisting
- Data sanitization
- Security event logging
- Service-level security controls

**Example Test:**
```python
async def test_input_validation_sql_injection(self, hass_with_config):
    """Test SQL injection input validation."""
    security_manager = hass.data[DOMAIN].get("security_manager")
    if security_manager:
        malicious_inputs = ["DROP TABLE users; --", "' OR '1'='1"]
        for input_text in malicious_inputs:
            is_valid, error_msg = security_manager.validate_input(input_text, "general", 1000)
            assert not is_valid
```

### 4. Performance Monitoring Tests (`test_performance_monitoring.py`)

Tests performance monitoring and alerting:

**Key Test Areas:**
- Request metrics recording
- Performance aggregation and trends
- Alert generation for performance issues
- Memory management and cleanup
- Concurrent request handling
- Performance threshold monitoring
- Health check functionality

**Example Test:**
```python
async def test_request_metrics_recording(self, hass_with_config):
    """Test recording of request metrics."""
    performance_monitor = hass.data[DOMAIN].get("performance_monitor")
    if performance_monitor:
        performance_monitor.record_request(
            request_id="test_req_123",
            request_type="query",
            provider="openai",
            duration_ms=1234.5,
            success=True
        )
        metrics = performance_monitor.get_metrics()
        assert metrics["total_requests"] == 1
```

### 5. Debugging System Tests (`test_debugging_system.py`)

Tests debugging and logging functionality:

**Key Test Areas:**
- Debug report generation
- System information collection
- Log retrieval and searching
- Structured logging functionality
- Error handling and recovery
- Component health monitoring
- Service availability checks

**Example Test:**
```python
async def test_generate_debug_report(self, hass_with_config):
    """Test comprehensive debug report generation."""
    result = await hass.services.async_call(
        DOMAIN, "generate_debug_report", {"entry_id": "test_entry"},
        blocking=True, return_result=True
    )
    assert "report_timestamp" in result
    assert "system_info" in result
    assert "recommendations" in result
```

### 6. MCP Integration Tests (`test_mcp_integration.py`)

Tests Model Context Protocol integration:

**Key Test Areas:**
- MCP server connection management
- Tool execution and error handling
- Connection retry logic
- Security integration with MCP
- Performance monitoring of MCP operations
- Error recovery and graceful degradation

**Example Test:**
```python
async def test_mcp_tool_execution(self, hass_with_config, mock_config_entry_pro):
    """Test MCP tool execution."""
    mcp_integration = hass.data[DOMAIN].get("mcp_integration")
    if mcp_integration:
        mock_result = {"success": True, "result": "Tool executed successfully"}
        with patch.object(mcp_integration, "execute_tool", return_value=mock_result):
            result = await mcp_integration.execute_tool("test_server", "test_tool", {"param": "value"})
            assert result["success"] is True
```

## Test Fixtures and Mocking

### Core Fixtures

- **`hass`**: Mock Home Assistant instance
- **`mock_config_entry`**: Mock configuration entry for testing
- **`mock_openai_client`**: Mock OpenAI API client
- **`sample_entities_data`**: Sample Home Assistant entities
- **`hass_with_config`**: Home Assistant instance with GLM Agent configured

### Mocking Strategy

1. **API Calls**: Mock all external API calls (OpenAI, web services)
2. **File Operations**: Mock file system operations for security
3. **Time Functions**: Mock time-based functions for deterministic testing
4. **Network Operations**: Mock network requests to prevent actual calls

### Environment Setup

Tests patch environment variables for consistent behavior:

```python
with patch.dict(os.environ, {
    'GLM_AGENT_STRUCTURED_LOGS': 'true',
    'GLM_AGENT_RATE_LIMITING': 'true',
    'GLM_AGENT_INPUT_VALIDATION': 'true'
}):
    # Test execution
```

## Test Data and Scenarios

### Security Test Scenarios

- **SQL Injection**: `DROP TABLE users; --`, `' OR '1'='1`
- **XSS**: `<script>alert('xss')</script>`, `javascript:alert('xss')`
- **Path Traversal**: `../../../etc/passwd`, `..\\..\\windows\\system32`
- **Command Injection**: `; rm -rf /`, `| cat /etc/passwd`

### Performance Test Scenarios

- **High Load**: 100+ concurrent requests
- **Slow Responses**: Requests exceeding 5 seconds
- **Large Data**: Responses > 1MB
- **Memory Stress**: Large numbers of metrics

### Error Scenarios

- **Network Failures**: Connection timeouts, DNS errors
- **API Errors**: Rate limiting, invalid responses
- **Configuration Errors**: Invalid API keys, malformed config
- **Resource Exhaustion**: Memory limits, file handle limits

## Continuous Integration

### GitHub Actions Workflow

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.12"
      - name: Install dependencies
        run: pip install -r requirements-dev.txt
      - name: Run tests
        run: pytest --cov=custom_components/glm_agent_ha --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

### Quality Gates

- **Test Coverage**: Minimum 80%
- **All Tests Pass**: Zero failing tests
- **Security Tests**: All security validations must pass
- **Performance Tests**: No performance regressions

## Test Best Practices

### 1. Test Isolation

Each test should be independent:
- Use fresh fixtures for each test
- Clean up state after tests
- Avoid dependencies between tests

### 2. Comprehensive Coverage

Test all code paths:
- Happy path scenarios
- Error conditions
- Edge cases
- Boundary conditions

### 3. Mocking Strategy

Mock external dependencies:
- API calls
- File system operations
- Network requests
- Time functions

### 4. Assertions

Use specific assertions:
- Check exact values where possible
- Verify behavior, not just implementation
- Include helpful error messages

### 5. Test Documentation

Document test purposes:
- Use descriptive test names
- Add comments for complex scenarios
- Document any special setup requirements

## Troubleshooting Tests

### Common Issues

1. **Import Errors**: Ensure Home Assistant is available or mocked properly
2. **Async Test Failures**: Use `await hass.async_block_till_done()` for async operations
3. **Mock Not Working**: Verify patch targets and mock setup
4. **Fixture Not Found**: Check fixture definitions and imports

### Debugging Tests

```bash
# Run with verbose output
pytest -v

# Run specific test with debugging
pytest tests/test_agent_services.py::TestQueryService::test_query_service_basic -v -s

# Stop on first failure
pytest -x

# Show local variables on failure
pytest --tb=long
```

### Performance Test Debugging

```bash
# Run performance tests with timing
pytest -m performance --durations=10

# Profile test execution
pytest --profile
```

## Test Maintenance

### Regular Tasks

1. **Update Tests**: When adding new features
2. **Review Coverage**: Ensure new code is covered
3. **Update Mocks**: When external APIs change
4. **Clean Up Tests**: Remove obsolete tests

### Test Review Checklist

- [ ] Test covers intended functionality
- [ ] Test is isolated and independent
- [ ] Assertions are specific and meaningful
- [ ] Mock setup is correct
- [ ] Test follows naming conventions
- [ ] Documentation is adequate

## Future Enhancements

### Planned Improvements

1. **End-to-End Tests**: Full integration tests with real Home Assistant
2. **Load Testing**: Performance tests under realistic load
3. **Security Penetration Testing**: Advanced security test scenarios
4. **Accessibility Testing**: UI and interaction accessibility tests
5. **Compatibility Testing**: Tests across different Home Assistant versions

### Test Metrics to Track

- Code coverage percentage
- Test execution time
- Number of test failures
- Test flakiness rate
- Performance regression detection

This comprehensive testing framework ensures that GLM Agent HA maintains high quality, security, and reliability throughout its development lifecycle.