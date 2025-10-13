# GLM Agent HA v1.05.0 Release Notes

## 🔧 Configuration Flow Improvements

GLM Agent HA v1.05.0 focuses on fixing configuration issues and simplifying the setup process for a better user experience.

## 🚀 What's Fixed

### Config Flow Fixes
- **"Invalid handler specified" Error**: Resolved critical config flow error that prevented proper integration setup
- **Undefined Model Reference**: Fixed `AVAILABLE_MODELS` reference issue that caused configuration failures
- **Simplified Configuration Process**: Streamlined the setup flow to reduce user friction

### Configuration Simplification
- **Reduced Complexity**: Removed custom model selection to streamline the setup process
- **Minimal Requirements**: Configuration now only requires:
  - API Token (for authentication)
  - Plan Selection (Lite/Pro/Max)
- **Better Error Handling**: Improved error messages and validation during setup
- **Enhanced Reliability**: More robust configuration process with better failure recovery

## 📋 Updated Setup Process

### Before (Complex)
1. Enter API token
2. Select custom model from dropdown
3. Choose plan type
4. Configure additional options
5. Validate configuration

### After (Simplified)
1. Enter API token
2. Choose plan type (Lite/Pro/Max)
3. Save and enjoy!

## 🛠️ Technical Changes

### Code Improvements
- **Config Flow Refactoring**: Simplified configuration flow logic
- **Error Handling**: Enhanced error detection and user feedback
- **Model Management**: Removed complex model selection logic
- **Validation**: Improved input validation and sanitization

### Files Modified
- `custom_components/glm_agent_ha/config_flow.py` - Streamlined configuration logic
- `custom_components/glm_agent_ha/__init__.py` - Updated model handling
- `custom_components/glm_agent_ha/manifest.json` - Version bump

## 🎯 User Benefits

### Easier Setup
- **Faster Installation**: Reduced setup time from multiple steps to just two
- **Fewer Errors**: Eliminated common configuration pitfalls
- **Better UX**: Cleaner, more intuitive configuration interface
- **Reliable**: More robust setup process with better error recovery

### Improved Experience
- **Clear Instructions**: Better guidance during setup
- **Instant Feedback**: Real-time validation and error reporting
- **Graceful Failures**: Better handling of configuration issues

## 🔒 Migration Notes

### For Existing Users
- **No Action Required**: Existing configurations will continue to work
- **Automatic Migration**: Custom model settings will be automatically migrated to plan-based selection
- **Backward Compatibility**: All existing functionality preserved

### For New Users
- **Simplified Setup**: Experience the streamlined configuration process
- **Quick Start**: Get up and running in just two steps
- **Better Documentation**: Updated setup guides and troubleshooting

## 🐛 Bug Fixes

- Fixed config flow "Invalid handler specified" error
- Resolved undefined `AVAILABLE_MODELS` reference
- Improved configuration validation
- Enhanced error messaging and user feedback
- Simplified model selection logic

## ⚠️ Breaking Changes

None. This release maintains full backward compatibility while improving the setup experience.

## 🙏 Acknowledgments

Thank you to the community members who reported configuration issues and provided valuable feedback that helped improve the setup process.

---

**Upgrade Instructions**: Update to v1.05.0 through HACS or manual installation. Existing users will experience no disruption to their configurations. New users will benefit from the simplified setup process.

**Support**: For issues and questions, please use the [GitHub Issues](https://github.com/johnneerdael/glm_agent_ha/issues) page.

---

# GLM Agent HA v1.03.0 Release Notes

## 🎉 Major New Feature: AI Task Entity Integration

GLM Agent HA v1.03.0 introduces powerful integration with Home Assistant's native AI Task API, enabling sophisticated structured data generation with image/video analysis capabilities.

## 🚀 What's New

### AI Task Entity
- **Full Home Assistant AI Task API Integration**: Native support for structured data generation tasks
- **Image/Video Attachment Support**: Process camera snapshots and other media sources
- **Structured Output Generation**: Convert natural language to structured JSON data
- **MCP Vision Integration**: Leverage Model Context Protocol for advanced vision analysis (Pro/Max plans)

### MCP Vision Workaround
Since GLM models lack native vision capabilities, we've implemented an innovative solution:
1. **Media Download**: Downloads images/videos from `media-source://` URIs
2. **URL Generation**: Saves to HA's `www` folder and generates publicly accessible URLs
3. **MCP Analysis**: Z.AI MCP analyzes images via URL access
4. **Context Enhancement**: Combines MCP analysis with user instructions
5. **GLM Processing**: Processes enhanced context with structured output

### Configuration Options
- `enable_ai_task`: Enable/disable AI Task entity
- `ha_base_url`: Configurable base URL for image hosting (e.g., `https://ha.netskope.pro`)
- `enable_mcp_integration`: Toggle MCP features (for Pro/Max plans)

## 📋 Example Use Cases

### Camera Analysis Automation
```yaml
actions:
  - alias: Analyze camera image
    action: ai_task.generate_data
    data:
      task_name: "camera_analysis"
      instructions: "Give a 1 sentence analysis of what is happening in this camera picture"
      structure:
        analysis:
          selector:
            text: null
      attachments:
        - media_content_id: media-source://camera.hallway
          media_content_type: ""
      entity_id: ai_task.glm_agent_ai_task
```

**Result**: `{"analysis": "A person wearing a blue jacket is walking through the hallway"}`

### Natural Language to Structured Data
```yaml
action: ai_task.generate_data
data:
  instructions: "Extract the room name and temperature from: 'Living room is currently 22°C'"
  structure:
    room:
      selector:
        text: null
    temperature:
      selector:
        number:
          min: -50
          max: 50
  entity_id: ai_task.glm_agent_ai_task
```

**Result**: `{"room": "Living room", "temperature": 22}`

## 🔧 Technical Implementation

### New Files Added
- `custom_components/glm_agent_ha/ai_task_entity.py` - Main AI Task entity implementation
- `custom_components/glm_agent_ha/ai_task/__init__.py` - AI Task platform setup
- `custom_components/glm_agent_ha/mcp_integration.py` - MCP server integration
- `tests/test_ai_agent_ha/test_ai_task_entity.py` - Comprehensive test suite
- `docs/HA_AI_INTEGRATION_PLAN.md` - Detailed integration architecture
- `docs/MCP_INTEGRATION.md` - MCP server documentation

### Key Features
- **Plan-Based Access**: MCP vision features available for Pro/Max plans
- **Error Handling**: Graceful degradation when MCP services are unavailable
- **Security**: Proper validation of media sources and URLs
- **Performance**: Efficient media handling with unique filename generation

### Dependencies Updated
- Added `media_source` and `ai_task` Home Assistant dependencies
- Updated OpenAI requirement to `~=1.55.0` for newer features

## 🏗️ Architecture

### Media Processing Flow
```
1. AI Task receives media-source://camera/hallway
2. Resolves to actual camera snapshot URL
3. Downloads image bytes
4. Saves to www/ai_task_20251013_220000_abc123.jpg
5. Generates URL: https://ha.netskope.pro/local/ai_task_20251013_220000_abc123.jpg
6. Passes URL to Z.AI MCP for analysis
7. MCP extracts: "A person wearing a blue jacket is walking through the hallway"
8. Combines with instructions and processes with GLM
9. Returns structured: {"analysis": "A person in a blue jacket is walking through the hallway"}
```

### MCP Integration
- **Z.AI MCP Server**: Image/video analysis services
- **Web Search MCP**: Enhanced information retrieval
- **Plan Restrictions**: Lite plan uses text-only, Pro/Max plans enable vision

## 🧪 Testing

- **334 lines of tests** for AI Task entity functionality
- **Test coverage**: Entity creation, media handling, MCP integration, error scenarios
- **Integration tests**: End-to-end AI Task workflows
- **Mock testing**: Comprehensive mocking of external dependencies

## 🔒 Security Considerations

- **Media Source Validation**: Proper validation of `media-source://` URIs
- **URL Generation**: Safe filename generation with hash-based uniqueness
- **Access Control**: MCP integration respects Home Assistant permissions
- **Data Privacy**: Temporary files managed securely with optional cleanup

## 📚 Documentation

- **User Guide**: Configuration and setup instructions
- **API Reference**: Detailed AI Task entity documentation
- **Integration Plan**: Complete architecture overview
- **MCP Documentation**: Server integration details

## 🔮 Future Roadmap

This release lays the foundation for:
- Phase 2: Conversation Entity implementation
- Phase 3: LLM API tool integration
- Enhanced multi-modal capabilities
- Advanced automation scenarios

## 🐛 Bug Fixes

- Improved error handling for media source resolution
- Enhanced logging for debugging MCP integration
- Better compatibility with different Home Assistant versions

## ⚠️ Breaking Changes

None. This is a feature-only release with backward compatibility maintained.

## 🙏 Acknowledgments

Special thanks to the Home Assistant community for the AI Task API framework and the Model Context Protocol specifications that enabled this integration.

---

**Upgrade Instructions**: Update to v1.03.0 through HACS or manual installation. Configure `ha_base_url` in integration options for proper image hosting. Enable MCP integration in Pro/Max plans for vision capabilities.

**Support**: For issues and questions, please use the [GitHub Issues](https://github.com/johnneerdael/glm_agent_ha/issues) page.