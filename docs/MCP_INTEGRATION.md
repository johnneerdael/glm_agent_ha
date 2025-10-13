# MCP Integration for GLM AI Agent HA

This document explains the Model Context Protocol (MCP) integration for the GLM AI Agent HA integration, which enables advanced capabilities like image analysis, video analysis, and web search for Pro and Max plan users.

## Overview

The MCP integration extends the GLM AI Agent HA with additional capabilities provided by Z.AI's MCP servers:

- **zai-mcp-server**: Provides image and video analysis capabilities
- **web-search-prime**: Provides web search functionality

These features are only available with GLM Coding Pro and GLM Coding Max plans.

## Plan Compatibility

### GLM Coding Lite
- Basic chat functionality only
- No MCP server access
- No image/video analysis
- No web search

### GLM Coding Pro
- All basic chat functionality
- Image analysis via `analyze_image` tool
- Video analysis via `analyze_video` tool
- Web search via `web_search` tool

### GLM Coding Max
- All Pro features
- Additional advanced capabilities
- Priority processing for MCP requests

## Configuration

### Plan Selection

During integration setup, users can select their plan:

1. Go to **Settings** > **Devices & Services**
2. Click **+ Add Integration**
3. Search for "GLM AI Agent HA"
4. Select your plan (Lite/Pro/Max)
5. Enter your API key
6. Complete the configuration

The integration will automatically configure MCP servers based on the selected plan.

### Automatic MCP Server Configuration

For Pro and Max plans, the integration automatically:

1. Detects the plan during configuration
2. Configures the appropriate MCP servers
3. Initializes connections during startup
4. Makes tools available to the AI agent

## Available Tools

### analyze_image

Analyzes an image and provides detailed description.

**Parameters:**
- `image_source` (required): URL or path to the image
- `prompt` (optional): Specific analysis prompt, defaults to "Analyze this image"

**Example:**
```
{
  "request_type": "data_request",
  "request": "analyze_image",
  "parameters": {
    "image_source": "https://example.com/image.jpg",
    "prompt": "Describe what objects are in this image"
  }
}
```

### analyze_video

Analyzes a video and provides detailed description.

**Parameters:**
- `video_source` (required): URL or path to the video
- `prompt` (optional): Specific analysis prompt, defaults to "Analyze this video"

**Example:**
```
{
  "request_type": "data_request",
  "request": "analyze_video",
  "parameters": {
    "video_source": "https://example.com/video.mp4",
    "prompt": "Summarize the main events in this video"
  }
}
```

### web_search

Searches the web for current information.

**Parameters:**
- `query` (required): Search query
- `count` (optional): Number of results to return, defaults to 5
- `search_recency_filter` (optional): Time filter for results, defaults to "noLimit"
  - Options: "noLimit", "day", "week", "month"

**Example:**
```
{
  "request_type": "data_request",
  "request": "web_search",
  "parameters": {
    "query": "latest news about artificial intelligence",
    "count": 10,
    "search_recency_filter": "week"
  }
}
```

## Usage Examples

### Image Analysis

User: "Can you analyze this security camera image and tell me if there's anything unusual?"

AI Response:
```
{
  "request_type": "data_request",
  "request": "analyze_image",
  "parameters": {
    "image_source": "https://example.com/security_camera.jpg",
    "prompt": "Check for any unusual objects or activities in this security camera image"
  }
}
```

### Web Search

User: "What's the weather forecast for tomorrow in New York?"

AI Response:
```
{
  "request_type": "data_request",
  "request": "web_search",
  "parameters": {
    "query": "weather forecast New York tomorrow",
    "count": 3,
    "search_recency_filter": "day"
  }
}
```

### Video Analysis

User: "Can you analyze this doorbell video and tell me who visited?"

AI Response:
```
{
  "request_type": "data_request",
  "request": "analyze_video",
  "parameters": {
    "video_source": "https://example.com/doorbell_video.mp4",
    "prompt": "Identify the people who appear in this doorbell video"
  }
}
```

## Technical Implementation

### MCP Integration Manager

The `MCPIntegrationManager` class handles:

- Plan validation and capability detection
- MCP server connection management
- Tool routing and execution
- Error handling and fallbacks

### Agent Integration

The `AiAgentHaAgent` class includes:

- MCP manager initialization
- Tool method implementations (`analyze_image`, `analyze_video`, `web_search`)
- Integration with the query processing pipeline
- Plan-specific capability checking

### System Prompt Updates

The system prompt is dynamically updated based on the plan:

- Lite: Basic tools only
- Pro/Max: Includes MCP tool descriptions and usage instructions

## Error Handling

### Plan Restrictions

If a user with a Lite plan attempts to use MCP tools:

```json
{
  "success": false,
  "error": "Image analysis is only available with Pro or Max plans",
  "plan_required": "pro"
}
```

### Connection Failures

If MCP servers are unavailable:

```json
{
  "success": false,
  "error": "MCP server not connected: zai-mcp-server"
}
```

### API Errors

If the Z.AI API returns an error:

```json
{
  "success": false,
  "error": "API error 401: Invalid API key"
}
```

## Troubleshooting

### MCP Tools Not Available

1. **Check Plan**: Verify you're using Pro or Max plan
2. **Check API Key**: Ensure your Z.AI API key is valid
3. **Check Configuration**: Verify MCP integration is enabled
4. **Check Logs**: Look for MCP connection errors in Home Assistant logs

### Image/Video Analysis Failures

1. **Check URL**: Ensure the image/video URL is accessible
2. **Check Format**: Verify the file format is supported
3. **Check Size**: Large files may timeout or fail
4. **Check Permissions**: Ensure the URL doesn't require authentication

### Web Search Issues

1. **Check Query**: Verify the search query is not too restrictive
2. **Check Filters**: Try adjusting the recency filter
3. **Check Connectivity**: Ensure internet access is available

## Development

### Adding New MCP Tools

To add new MCP tools:

1. Update `MCPIntegrationManager._get_server_for_tool()` to map the tool
2. Add the tool implementation in `MCPIntegrationManager`
3. Update the system prompt in `AiAgentHaAgent`
4. Add the tool to the data request types list
5. Add handling in `AiAgentHaAgent.process_query()`
6. Create tests for the new functionality

### Testing MCP Integration

Run the MCP integration tests:

```bash
pytest tests/test_ai_agent_ha/test_mcp_integration.py -v
```

## Security Considerations

- API keys are stored securely in Home Assistant's configuration
- MCP server connections use HTTPS encryption
- Image/video URLs should be from trusted sources
- Web search queries are logged for debugging purposes

## Future Enhancements

Potential future MCP integrations:

- Additional image analysis models
- Video transcription services
- Real-time data feeds
- Specialized domain search
- Document analysis capabilities