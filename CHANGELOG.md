# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.03.0] - 2025-10-13

### Added
- **AI Task Entity Integration**: Full integration with Home Assistant's AI Task API
  - Structured data generation with support for image/video attachments
  - MCP (Model Context Protocol) vision integration for Pro/Max plans
  - Media handling for camera snapshots and other media sources
  - Configurable base URL for image hosting via HA's www folder

### Features
- **MCP Vision Workaround**: Clever solution for GLM models lacking native vision
  - Downloads media to HA's www folder
  - Generates publicly accessible URLs for MCP analysis
  - Combines MCP analysis results with user instructions
  - Processes enhanced context with GLM for structured output

### Technical Implementation
- New `GLMAgentAITaskEntity` class extending Home Assistant's `AITaskEntity`
- AI Task platform setup and registration
- Media download and save functionality with unique filename generation
- MCP integration for Z.AI image/video analysis services
- Comprehensive error handling and graceful degradation
- Full test coverage for AI Task entity functionality

### Configuration
- New configuration options:
  - `enable_ai_task`: Enable/disable AI Task entity
  - `ha_base_url`: Base URL for image hosting (e.g., `https://ha.netskope.pro`)
  - `enable_mcp_integration`: MCP feature toggle (for Pro/Max plans)

### Dependencies
- Added `media_source` and `ai_task` Home Assistant dependencies
- Updated OpenAI requirement to `~=1.55.0` for newer features

### Example Use Cases
- Camera analysis automations with structured output
- Image/video content analysis via MCP services
- Natural language to structured data conversion
- Home Assistant automation integration with AI-powered insights

## [1.02.0] - 2025-10-13

### Added
- **MCP Server Integration**: Support for Model Context Protocol servers
  - Z.AI MCP server integration for image/video analysis
  - Web search capabilities via MCP
  - Plan-based feature access (Pro/Max plans)

### Features
- **Plan Selection**: Lite/Pro/Max plan configuration with capability-based features
- **Image Analysis**: Z.AI MCP integration for image and video content analysis
- **Web Search**: MCP-powered web search functionality
- **Structured Output**: Enhanced JSON response formatting and validation

## [1.01.7] - Previous

### Features
- Basic GLM Agent HA integration
- Query service for natural language processing
- Dashboard creation and automation services
- Configuration flow for OpenAI provider setup
- Frontend panel integration