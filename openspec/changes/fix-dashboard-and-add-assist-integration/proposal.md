## Why
The GLM Agent HA integration has a broken dashboard showing JavaScript errors and is missing critical features: an LLM assistant for Home Assistant's Assist pipeline and AI task entities that should be available under the integration device. These issues prevent users from fully utilizing the integration's capabilities and break the expected user experience.

## What Changes
- **BREAKING**: Fix the broken dashboard JavaScript errors and ensure proper frontend loading
- Add LLM assistant provider for Home Assistant's Assist pipeline integration
- Implement AI task entities under the integration device for task management
- Improve error handling and fallback mechanisms for dashboard failures
- Ensure proper device registration and entity discovery

## Impact
- Affected specs: dashboard-ui, assist-pipeline, ai-task-entities
- Affected code: frontend/dashboard.html, assist_pipeline integration, device registry, entity management
- Dependencies: Home Assistant Assist pipeline API, device registry service