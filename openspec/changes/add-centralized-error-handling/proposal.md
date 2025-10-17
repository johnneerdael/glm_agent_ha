## Why
The GLM Coding Plan Agent HA integration has multiple complex components (MCP integration, AI tasks, voice pipeline, HTTP routes) that currently have scattered error handling. When issues occur, users and developers lack centralized visibility into system health, making debugging difficult. Recent HTTP registration bugs demonstrated the need for better error monitoring and user-friendly error reporting.

## What Changes
- Add centralized error handling system to collect, categorize, and report errors from all components
- Implement health monitoring for critical subsystems (MCP connections, HTTP routes, AI task pipeline)
- Create diagnostic dashboard with real-time system status and error analytics
- Add proactive error recovery mechanisms with exponential backoff
- Implement error reporting service for users to export diagnostics
- **BREAKING**: Update error handling patterns throughout the codebase to use centralized system

## Impact
- Affected specs: error-handling (new)
- Affected code: All integration components (__init__.py, mcp_integration.py, ai_task_pipeline.py, voice_pipeline.py, agent.py)
- User impact: Better error visibility, improved debugging, proactive health monitoring