## Why
The GLM Agent HA integration is experiencing critical failures that prevent proper operation: MCP servers are failing to connect with HTTP 400 errors, static route registration is causing runtime conflicts with duplicate GET routes, and translation string context variables are missing. These issues break the integration setup, prevent MCP-enhanced capabilities from loading, and cause user-facing errors in the configuration interface.

## What Changes
- **BREAKING**: Fix HTTP static route registration conflicts by implementing proper route deduplication and cleanup
- Implement native FastMCP integration for Python-based MCP servers instead of external HTTP MCP servers
- Add robust error handling and fallback mechanisms for MCP connection failures
- Fix missing translation context variables for configuration strings
- Improve integration setup reliability with proper error recovery and retry logic
- Add comprehensive logging for troubleshooting MCP and HTTP routing issues

## Impact
- Affected specs: mcp-integration, http-routing, localization
- Affected code: mcp_integration.py, __init__.py (HTTP routing), config_flow.py (translations)
- Dependencies: FastMCP library, Home Assistant HTTP router API, translation framework
- Migration: External HTTP MCP servers will be replaced with native Python implementations