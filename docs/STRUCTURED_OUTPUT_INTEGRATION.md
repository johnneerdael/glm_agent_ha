# Structured Output Integration with Home Assistant AI Tasks

This document explains how the GLM AI Agent HA integration now supports structured output for Home Assistant's AI Task `generate_data` service.

## Overview

The integration has been enhanced to support structured output enforcement, ensuring that when Home Assistant's AI Task service requests specific JSON schemas, the GLM model returns properly formatted JSON responses.

## Key Features

### 1. JSON Mode Enforcement

When a structured output schema is provided, the integration automatically:
- Enables JSON mode in the GLM API request using `response_format: {"type": "json_object"}`
- Injects the schema into the system prompt with explicit instructions
- Provides corrective retry if JSON parsing fails

### 2. Schema Injection

The system injects a strict schema instruction when structured output is required:

```python
schema_instruction = (
    "You MUST return a single valid JSON object that exactly matches this schema:\n"
    f"{json.dumps(structure, indent=2)}\n"
    "Do NOT wrap the JSON in code blocks, add explanations, or include any text outside the JSON."
)
```

### 3. Corrective Retry Mechanism

If JSON parsing fails despite JSON mode enforcement, the system automatically:
- Detects the parsing failure
- Adds a corrective system message asking for pure JSON
- Retries the request within the iteration limit

## Implementation Details

### OpenAI Client Changes

```python
async def get_response(self, messages, response_format=None, **kwargs):
    # Build payload with model-appropriate parameters
    payload = {"model": self.model, "messages": messages, token_param: 2048}
    if response_format:
        payload["response_format"] = response_format  # {"type": "json_object"}
```

### Agent Process Query Changes

```python
async def process_query(self, user_query: str, structure: Optional[Dict[str, Any]] = None):
    # Detect structured output requirement
    enforce_json = bool(structure)
    
    # Add schema instruction if needed
    if enforce_json and structure:
        schema_instruction = (
            "You MUST return a single valid JSON object that exactly matches this schema:\n"
            f"{json.dumps(structure, indent=2)}\n"
            "Do NOT wrap the JSON in code blocks, add explanations, or include any text outside the JSON."
        )
        self.conversation_history.append({"role": "system", "content": schema_instruction})
    
    # Get response with JSON mode enforcement
    response = await self._get_ai_response(enforce_json=enforce_json)
```

### Service Handler Integration

The query service handler now properly forwards the `structure` parameter:

```python
async def async_handle_query(call):
    agent = hass.data[DOMAIN]["agents"][provider]
    result = await agent.process_query(
        call.data.get("prompt", ""),
        provider=provider,
        model=call.data.get("model"),
        structure=call.data.get("structure"),  # Forward schema to agent
    )
```

## Usage Examples

### Home Assistant AI Task Integration

When using Home Assistant's AI Task with `generate_data`, the integration will automatically:

1. Receive the schema from the AI Task service
2. Enable JSON mode in the GLM API request
3. Inject the schema into the system prompt
4. Ensure the response matches the required format

### Example Schema

```json
{
  "type": "object",
  "properties": {
    "device_name": {"type": "string"},
    "state": {"type": "string"},
    "brightness": {"type": "number"}
  },
  "required": ["device_name", "state"]
}
```

### Expected Response

```json
{
  "request_type": "final_response",
  "response": {
    "device_name": "Living Room Light",
    "state": "on",
    "brightness": 255
  }
}
```

## Error Handling

### JSON Parsing Failures

If the GLM model returns non-JSON content despite JSON mode:

1. The system detects the parsing failure
2. Adds a corrective instruction: "The previous response was not valid JSON. Please respond with ONLY a valid JSON object."
3. Retries the request automatically

### Logging

Enhanced logging provides visibility into:
- When JSON mode is enforced
- Schema injection details
- Corrective retry attempts
- Response format validation

## Testing

The integration includes comprehensive tests for:
- JSON mode enforcement in the OpenAI client
- Schema injection in the agent
- Corrective retry mechanisms
- Service handler parameter forwarding

Run tests with:
```bash
pytest tests/test_ai_agent_ha/test_structured_output.py -v
```

## Compatibility

This feature is compatible with:
- Home Assistant 2024.1+
- GLM models that support JSON mode (GLM-4.5, GLM-4.6, GLM-4.5-air)
- All existing GLM AI Agent HA functionality

## Troubleshooting

### Common Issues

1. **JSON parsing errors**: Check logs for corrective retry attempts
2. **Schema validation failures**: Verify the schema is properly formatted
3. **Model compatibility**: Ensure using a GLM model that supports JSON mode

### Debug Logging

Enable debug logging to trace structured output processing:

```yaml
logger:
  logs:
    custom_components.glm_agent_ha: debug
```

This will show detailed information about:
- Schema injection
- JSON mode enforcement
- Response parsing attempts
- Corrective retry actions