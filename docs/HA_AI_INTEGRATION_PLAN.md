# Home Assistant AI Integration Plan

## Overview

This document outlines the plan to fully integrate the GLM Agent HA with Home Assistant's native AI capabilities, including:
1. **AI Task Entity** - For structured data generation with image/video analysis support
2. **Conversation Entity** - For natural language interactions with LLM API support
3. **MCP Vision Integration** - Clever workaround for image analysis with non-vision LLMs

## Current State

### Completed Features
- ✅ Structured output support via `response_format` parameter
- ✅ MCP integration for Pro/Max plans (Z.AI image/video analysis, web search)
- ✅ Plan selection (Lite/Pro/Max) with capability-based features
- ✅ Basic query service (`glm_agent_ha.query`)
- ✅ Dashboard creation and automation services

### Gap Analysis
- ❌ No AI Task entity implementation
- ❌ No Conversation entity implementation  
- ❌ No LLM API registration for tool use
- ❌ Attachments (images/videos) not handled via AI Task API
- ❌ ChatLog integration not implemented

## Architecture Design

### 1. AI Task Entity (`AITaskEntity`)

**Purpose**: Enable structured data generation tasks with support for image/video attachments.

**Key Challenge**: GLM models don't have native vision capabilities, but we can use MCP Z.AI for image/video analysis.

**Solution Pattern**:
```python
class GLMAgentAITaskEntity(AITaskEntity):
    """AI Task entity for GLM Agent HA."""
    
    async def _async_generate_data(
        self, 
        task: GenDataTask, 
        chat_log: ChatLog
    ) -> GenDataTaskResult:
        # Step 1: Process attachments using MCP (if Pro/Max plan)
        attachment_analyses = []
        if task.attachments and self._has_mcp_support():
            for attachment in task.attachments:
                # Download media and save to www folder for MCP access
                public_url = await self._download_and_save_media(attachment.media_content_id)
                
                # Analyze using Z.AI MCP with public URL
                analysis = await self._mcp_manager.analyze_image(
                    public_url,  # MCP requires URL, not bytes
                    prompt="Describe this image in detail for AI analysis"
                )
                attachment_analyses.append(analysis)
        
        # Step 2: Combine instructions + attachment analyses
        enhanced_instructions = task.instructions
        if attachment_analyses:
            enhanced_instructions = f"""
{task.instructions}

Context from attached media:
{chr(10).join(f"- {analysis}" for analysis in attachment_analyses)}
"""
        
        # Step 3: Generate structured data using GLM + structured output
        result = await self._agent.process_query(
            prompt=enhanced_instructions,
            structure=task.structure,
            chat_log=chat_log
        )
        
        return GenDataTaskResult(
            conversation_id=chat_log.conversation_id,
            data=result
        )
```

**Implementation Files**:
- `custom_components/glm_agent_ha/ai_task_entity.py` - New file
- Update `custom_components/glm_agent_ha/__init__.py` - Register entity platform
- Update `custom_components/glm_agent_ha/manifest.json` - Add dependencies

### 2. Conversation Entity (`ConversationEntity`)

**Purpose**: Enable natural language conversations with Home Assistant via GLM Agent.

**Key Features**:
- Support for multi-turn conversations via ChatLog
- LLM API tool integration
- Streaming responses
- Context-aware interactions

**Solution Pattern**:
```python
class GLMAgentConversationEntity(ConversationEntity):
    """Conversation entity for GLM Agent HA."""
    
    async def async_process(
        self, 
        user_input: ConversationInput
    ) -> ConversationResult:
        # Step 1: Get or create chat log
        chat_log = await self._get_chat_log(user_input.conversation_id)
        
        # Step 2: Provide LLM context (tools, prompts)
        try:
            await chat_log.async_provide_llm_data(
                user_input.as_llm_context(DOMAIN),
                self.entry.options.get(CONF_LLM_HASS_API),
                self.entry.options.get(CONF_PROMPT),
                user_input.extra_system_prompt,
            )
        except ConverseError as err:
            return err.as_conversation_result()
        
        # Step 3: Format tools for GLM
        tools = None
        if chat_log.llm_api:
            tools = [
                self._format_tool_for_glm(tool)
                for tool in chat_log.llm_api.tools
            ]
        
        # Step 4: Build message history
        messages = [
            self._convert_content(content)
            for content in chat_log.content
        ]
        
        # Step 5: Iterative tool calling loop
        for iteration in range(10):
            # Call GLM with tools
            response = await self._agent.get_response_stream(
                messages=messages,
                tools=tools
            )
            
            # Stream response and handle tool calls
            async for content in chat_log.async_add_delta_content_stream(
                user_input.agent_id,
                self._transform_stream(response)
            ):
                messages.append(self._convert_content(content))
            
            # Break if no more tool calls needed
            if not chat_log.unresponded_tool_results:
                break
        
        # Step 6: Return final response
        intent_response = intent.IntentResponse(language=user_input.language)
        intent_response.async_set_speech(chat_log.content[-1].content or "")
        return ConversationResult(
            response=intent_response,
            conversation_id=chat_log.conversation_id,
        )
```

**Implementation Files**:
- `custom_components/glm_agent_ha/conversation_entity.py` - New file
- Update `custom_components/glm_agent_ha/__init__.py` - Register entity platform

### 3. LLM API Registration

**Purpose**: Register Home Assistant's built-in Assist API for tool use with GLM Agent.

**Implementation**:
```python
# In __init__.py async_setup_entry

from homeassistant.helpers import llm

# Register LLM API if user enables it in options
if entry.options.get(CONF_ENABLE_LLM_API, True):
    api = llm.async_get_api(hass, "assist")  # Use built-in Assist API
    entry.async_on_unload(
        llm.async_register_api(hass, api)
    )
```

**Config Flow Updates**:
```python
# In config_flow.py - Options flow

vol.Optional(
    CONF_LLM_HASS_API,
    description={"suggested_value": options.get(CONF_LLM_HASS_API, ["assist"])},
): SelectSelector(
    SelectSelectorConfig(
        options=[
            SelectOptionDict(label=api.name, value=api.id)
            for api in llm.async_get_apis(hass)
        ],
        multiple=True
    )
),
```

### 4. Media Handling for AI Task

**Challenge**: AI Task attachments use `media-source://` URIs that need to be resolved and downloaded, then made accessible to MCP servers.

**Important MCP Limitation**: Z.AI MCP server cannot process images directly from the client's paste buffer (the client transcodes and sends to model directly). MCP servers require local file paths or publicly accessible URLs.

**Solution - Two-Step Process**:

1. **Download and Save to HA's `www` Folder**:
```python
async def _download_and_save_media(self, media_content_id: str) -> str:
    """Download media and save to www folder, return public URL."""
    from homeassistant.components.media_source import async_resolve_media
    import os
    import hashlib
    from datetime import datetime
    
    # Resolve media source
    media = await async_resolve_media(self.hass, media_content_id, None)
    
    # Download media content
    async with self.hass.helpers.aiohttp_client.async_get_clientsession().get(
        media.url
    ) as response:
        media_bytes = await response.read()
    
    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    content_hash = hashlib.md5(media_bytes).hexdigest()[:8]
    extension = media_content_id.split('.')[-1] or 'jpg'
    filename = f"ai_task_{timestamp}_{content_hash}.{extension}"
    
    # Save to HA's www folder
    www_path = os.path.join(self.hass.config.path("www"), filename)
    
    # Ensure www directory exists
    os.makedirs(os.path.dirname(www_path), exist_ok=True)
    
    with open(www_path, 'wb') as f:
        f.write(media_bytes)
    
    # Return public URL (configurable base URL)
    base_url = self.entry.options.get(CONF_HA_BASE_URL, "http://homeassistant.local:8123")
    public_url = f"{base_url}/local/{filename}"
    
    return public_url
```

2. **Analyze via MCP with URL Reference**:
```python
async def _analyze_media_with_mcp(self, public_url: str) -> str:
    """Analyze media using MCP with public URL."""
    # MCP server can now access the image via URL
    analysis = await self._mcp_manager.analyze_image(
        public_url,  # Use URL instead of bytes
        prompt="Describe this image in detail for AI analysis"
    )
    return analysis
```

**Complete Image Processing Flow**:
1. Receive `media-source://camera/camera.hallway` from AI Task
2. Resolve to actual camera snapshot URL
3. Download image bytes
4. Save to HA's `www/ai_task_{timestamp}_{hash}.jpg`
5. Generate public URL: `{ha_base_url}/local/ai_task_{timestamp}_{hash}.jpg`
6. Pass URL (not bytes) to Z.AI MCP `analyze_image` tool
7. MCP downloads from URL and analyzes
8. Get textual description back
9. Combine with task instructions
10. Process with GLM (which now has image context as text)
11. Optionally clean up temp file after analysis

**Configuration Requirements**:
- Add `CONF_HA_BASE_URL` to config options (default: auto-detect from HA)
- Ensure `www` folder is accessible
- Implement cleanup job for old temp files (optional)

## Implementation Phases

### Phase 1: AI Task Entity (Priority: HIGH)
**Timeline**: 2-3 days

1. Create `ai_task_entity.py` with `GLMAgentAITaskEntity`
2. Implement `_async_generate_data` method
3. Add media download and MCP analysis logic
4. Register entity platform in `__init__.py`
5. Add tests in `tests/test_ai_agent_ha/test_ai_task_entity.py`
6. Update manifest dependencies

**Deliverables**:
- Working AI Task entity
- Image/video analysis via MCP
- Structured output support
- Tests and documentation

### Phase 2: Conversation Entity (Priority: MEDIUM)
**Timeline**: 3-4 days

1. Create `conversation_entity.py` with `GLMAgentConversationEntity`
2. Implement `async_process` method
3. Add LLM API tool formatting
4. Implement streaming responses
5. Add tool calling loop logic
6. Add tests in `tests/test_ai_agent_ha/test_conversation_entity.py`

**Deliverables**:
- Working Conversation entity
- LLM API tool support
- Multi-turn conversations
- Tests and documentation

### Phase 3: LLM API Integration (Priority: MEDIUM)
**Timeline**: 1-2 days

1. Update config flow to include LLM API selection
2. Register APIs in `__init__.py`
3. Update conversation entity to use selected APIs
4. Add tests for LLM API integration

**Deliverables**:
- User-selectable LLM APIs
- Tool use support
- Tests and documentation

### Phase 4: Integration Testing & Documentation (Priority: HIGH)
**Timeline**: 2-3 days

1. Create comprehensive integration tests
2. Test AI Task with camera snapshots
3. Test Conversation with tool use
4. Write user documentation
5. Create example automations

**Deliverables**:
- Full integration test suite
- User guide for AI Task
- User guide for Conversation
- Example automations

## Example Use Cases

### Use Case 1: Camera Analysis Automation
```yaml
actions:
  - variables:
      camera_entity: camera.hallway_2nd_floor
      extra_instructions: >-
        Provide information about what you see in the last 5 minutes.
  - delay:
      seconds: 5
  - alias: Analyze camera image
    action: ai_task.generate_data
    data:
      task_name: "{{ this.entity_id }}"
      instructions: >
        Give a 1 sentence analysis of what is happening in this camera picture.
        {{ extra_instructions }}
      structure:
        analysis:
          selector:
            text: null
      attachments:
        - media_content_id: media-source://camera/{{ camera_entity }}
          media_content_type: ""
      entity_id: ai_task.glm_agent_ai_task
```

**Behind the Scenes**:
1. AI Task receives camera snapshot media source
2. Downloads latest camera image
3. Sends to Z.AI MCP for analysis
4. Z.AI returns: "A person wearing a blue jacket is walking through the hallway"
5. Combines with instructions: "Give 1 sentence analysis... [person in blue jacket...]"
6. GLM generates structured response: `{"analysis": "A person in a blue jacket is walking through the hallway"}`
7. Returns result to automation

### Use Case 2: Natural Language Home Control
```yaml
# User says: "Turn on the lights in the living room and set them to 50%"
# Via Conversation entity with LLM API tools
```

**Behind the Scenes**:
1. Conversation entity receives user input
2. Provides LLM API tools (light.turn_on, etc.)
3. GLM decides to call tools:
   - `light.turn_on(entity_id="light.living_room", brightness_pct=50)`
4. Conversation entity executes tool
5. Returns result: "I've turned on the living room lights to 50% brightness"

## Testing Strategy

### Unit Tests
- `test_ai_task_entity.py` - AI Task entity functionality
- `test_conversation_entity.py` - Conversation entity functionality  
- `test_media_handling.py` - Media download and processing
- `test_llm_api_integration.py` - LLM API registration and usage

### Integration Tests
- `test_ai_task_with_camera.py` - Full camera analysis workflow
- `test_conversation_with_tools.py` - Tool calling workflows
- `test_structured_output_ai_task.py` - Structured output generation

### Manual Testing Scenarios
1. Camera snapshot analysis via AI Task
2. Multi-turn conversation via Conversation entity
3. Tool use via Conversation entity
4. Structured output generation
5. Plan-based capability restrictions

## Dependencies & Manifest Updates

```json
{
  "domain": "glm_agent_ha",
  "name": "GLM Agent HA",
  "dependencies": [
    "media_source",
    "conversation",
    "ai_task",
    "llm"
  ],
  "requirements": [
    "openai>=1.0.0"
  ]
}
```

## Configuration Schema

### Config Entry Data
```python
{
    "ai_provider": "openai",
    "openai_token": "glm-xxx",
    "models": {"openai": "GLM-4.6"},
    "plan": "pro",  # or "lite", "max"
}
```

### Config Entry Options
```python
{
    "llm_hass_api": ["assist"],  # Selected LLM APIs
    "prompt": "You are a helpful assistant...",  # Custom system prompt
    "enable_ai_task": True,  # Enable AI Task entity
    "enable_conversation": True,  # Enable Conversation entity
}
```

## Success Criteria

### Phase 1 (AI Task) Success
- [ ] AI Task entity registered and visible in HA
- [ ] Camera snapshots successfully analyzed via MCP
- [ ] Structured output correctly generated
- [ ] Tests pass with >90% coverage
- [ ] Documentation complete

### Phase 2 (Conversation) Success
- [ ] Conversation entity registered and visible in HA
- [ ] Multi-turn conversations work correctly
- [ ] LLM API tools correctly formatted and called
- [ ] Streaming responses work
- [ ] Tests pass with >90% coverage

### Phase 3 (LLM API) Success
- [ ] LLM APIs selectable in config flow
- [ ] Tools correctly passed to GLM
- [ ] Tool calls executed and results returned
- [ ] Tests pass with >90% coverage

### Phase 4 (Integration) Success
- [ ] End-to-end camera analysis automation works
- [ ] End-to-end conversation with tools works
- [ ] All tests pass
- [ ] User documentation complete
- [ ] Example automations provided

## Risk Mitigation

### Risk 1: MCP Connection Failures
**Mitigation**: 
- Implement retry logic with exponential backoff
- Graceful degradation (skip image analysis if MCP unavailable)
- Clear error messages to user

### Risk 2: Media Source Resolution Issues
**Mitigation**:
- Comprehensive error handling for media download
- Support multiple media source types
- Fallback to direct URL if media source fails

### Risk 3: Tool Calling Complexity
**Mitigation**:
- Start with simple tool use cases
- Extensive testing of tool formatting
- Clear documentation of limitations

### Risk 4: Performance with Large Images
**Mitigation**:
- Implement image size limits
- Compress images before sending to MCP
- Async processing to avoid blocking

## Next Steps

1. ✅ Research Home Assistant AI APIs (COMPLETE)
2. ✅ Create detailed implementation plan (COMPLETE)
3. Review plan with user
4. Begin Phase 1 implementation (AI Task Entity)
5. Iteratively implement and test each phase
6. Gather user feedback and iterate

## Questions for User

1. Should we implement both AI Task and Conversation entities, or prioritize one?
2. What are the most important use cases to support initially?
3. Should we support custom LLM APIs beyond the built-in Assist API?
4. Any specific camera models or media sources to prioritize?
5. What structured output formats are most important for your use cases?