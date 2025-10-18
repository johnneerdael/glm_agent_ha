"""Support for Anthropic conversation."""
from __future__ import annotations

import logging
import json
from typing import Literal, Dict, List, Any, Optional, cast
from collections.abc import AsyncGenerator, Callable
from homeassistant.helpers import template

try:
    from voluptuous_openapi import convert
    HAS_VOLUPTUOUS_OPENAPI = True
except ImportError:
    HAS_VOLUPTUOUS_OPENAPI = False
    
    def convert(schema, custom_serializer=None):
        """Fallback convert function when voluptuous_openapi is not available."""
        if hasattr(schema, "to_dict"):
            return schema.to_dict()
        if hasattr(schema, "__dict__"):
            return schema.__dict__
        return {"type": "object", "properties": {}}

# Define our own APIError class for compatibility
class APIError(Exception):
    """API Error."""

    def __init__(self, message, type, status_code):
        """Initialize the error."""
        self.message = message
        self.type = type
        self.status_code = status_code
        super().__init__(message)

from homeassistant.components import conversation as ha_conversation, assist_pipeline
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID, MATCH_ALL, CONF_LLM_HASS_API
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import intent, template, llm, device_registry as dr, translation
from homeassistant.util import ulid

from .const import (
    CONF_API_KEY,
    CONF_CHAT_MODEL,
    CONF_CONTROL_HA,
    CONF_MAX_TOKENS,
    CONF_PROMPT,
    CONF_RECOMMENDED_SETTINGS,
    CONF_TEMPERATURE,
    DEFAULT_CONTROL_HA,
    DEFAULT_MAX_TOKENS,
    DEFAULT_PROMPT,
    DEFAULT_TEMPERATURE,
    AnthropicModels,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

# Max number of back and forth with the LLM to generate a response
MAX_TOOL_ITERATIONS = 10


def _format_tool(
    tool: llm.Tool, custom_serializer: Callable[[Any], Any] | None
) -> Dict[str, Any]:
    """Format tool specification for Anthropic."""
    return {
        "name": tool.name,
        "description": tool.description or "",
        "input_schema": convert(tool.parameters, custom_serializer=custom_serializer),
        "type": "custom"
    }


def _convert_content_to_param(
    content: ha_conversation.Content,
) -> List[Dict[str, Any]]:
    """Convert any native chat message for this agent to the Anthropic format."""
    messages = []
    
    if isinstance(content, ha_conversation.ToolResultContent):
        return [{
            "role": "user",
            "content": [{
                "type": "tool_result",
                "tool_use_id": content.tool_call_id,
                "content": json.dumps(content.tool_result)
            }]
        }]

    if content.content:
        if content.role == "user":
            messages.append({
                "role": "user",
                "content": [{"type": "text", "text": content.content}]
            })
        elif content.role == "assistant":
            messages.append({
                "role": "assistant",
                "content": [{"type": "text", "text": content.content}]
            })

    if isinstance(content, ha_conversation.AssistantContent) and content.tool_calls:
        for tool_call in content.tool_calls:
            messages.append({
                "role": "assistant",
                "content": [{
                    "type": "tool_use",
                    "id": tool_call.id,
                    "name": tool_call.tool_name,
                    "input": tool_call.tool_args
                }]
            })
    
    return messages


async def _transform_stream(
    chat_log: ha_conversation.ChatLog,
    response: Any,
) -> AsyncGenerator[ha_conversation.AssistantContentDeltaDict]:
    """Transform an Anthropic response into HA format."""
    # Since Anthropic doesn't support streaming yet, we'll simulate it
    # by yielding the entire response at once
    
    response_text = ""
    tool_calls = []
    
    # Extract content from response
    if hasattr(response, "content") and response.content:
        for content_item in response.content:
            if hasattr(content_item, "type"):
                if content_item.type == "text":
                    response_text = content_item.text
                elif content_item.type == "tool_use":
                    # Convert to the format expected by chat_log
                    tool_calls.append(
                        llm.ToolInput(
                            id=content_item.id,
                            tool_name=content_item.name,
                            tool_args=content_item.input,
                        )
                    )
            elif isinstance(content_item, dict):
                if content_item.get("type") == "text":
                    response_text = content_item.get("text", "")
                elif content_item.get("type") == "tool_use":
                    # Convert to the format expected by chat_log
                    tool_calls.append(
                        llm.ToolInput(
                            id=content_item.get("id", ""),
                            tool_name=content_item.get("name", ""),
                            tool_args=content_item.get("input", {}),
                        )
                    )
    
    # If we have text content, yield it
    if response_text:
        yield {"role": "assistant"}
        yield {"content": response_text}
    
    # If we have tool calls, yield them
    for tool_call in tool_calls:
        yield {
            "tool_calls": [tool_call]
        }


class AnthropicAgent(ha_conversation.AbstractConversationAgent, ha_conversation.ConversationEntity):
    """Anthropic conversation agent."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: Any,  # Use Any for the client type
    ) -> None:
        """Initialize the agent."""
        self.hass = hass
        self.entry = entry
        self.client = client
        self.prompt = entry.options.get(CONF_PROMPT, DEFAULT_PROMPT)
        self.model = entry.options.get(
            CONF_CHAT_MODEL, AnthropicModels.default()
        )
        # Принудительное приведение типов для предотвращения ошибок API
        max_tokens_raw = entry.options.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)
        temperature_raw = entry.options.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE)
        
        try:
            self.max_tokens = int(max_tokens_raw) if max_tokens_raw is not None else DEFAULT_MAX_TOKENS
        except (ValueError, TypeError) as err:
            _LOGGER.warning("Invalid max_tokens value '%s', using default: %s", max_tokens_raw, err)
            self.max_tokens = DEFAULT_MAX_TOKENS
            
        try:
            self.temperature = float(temperature_raw) if temperature_raw is not None else DEFAULT_TEMPERATURE
        except (ValueError, TypeError) as err:
            _LOGGER.warning("Invalid temperature value '%s', using default: %s", temperature_raw, err)
            self.temperature = DEFAULT_TEMPERATURE
        self.control_ha = entry.options.get(CONF_CONTROL_HA, DEFAULT_CONTROL_HA)
        self.recommended_settings = entry.options.get(CONF_RECOMMENDED_SETTINGS, True)
        self._attr_unique_id = entry.entry_id
        self._attr_device_info = dr.DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            manufacturer="Anthropic",
            model="Claude",
            entry_type=dr.DeviceEntryType.SERVICE,
        )
        if self.control_ha:
            self._attr_supported_features = (
                ha_conversation.ConversationEntityFeature.CONTROL
            )
        
        # Cache for translations
        self._translations_cache = {}
        
    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        """Return a list of supported languages."""
        return MATCH_ALL
        
    async def async_added_to_hass(self) -> None:
        """When entity is added to Home Assistant."""
        await super().async_added_to_hass()
        assist_pipeline.async_migrate_engine(
            self.hass, "conversation", self.entry.entry_id, self.entity_id
        )
        ha_conversation.async_set_agent(self.hass, self.entry, self)
        self.entry.async_on_unload(
            self.entry.add_update_listener(self._async_entry_update_listener)
        )

    async def async_will_remove_from_hass(self) -> None:
        """When entity will be removed from Home Assistant."""
        ha_conversation.async_unset_agent(self.hass, self.entry)
        await super().async_will_remove_from_hass()
        
    async def async_process(
        self, user_input: ha_conversation.ConversationInput
    ) -> ha_conversation.ConversationResult:
        """Process a sentence."""
        try:
            # Create a chat log for this conversation
            conversation_id = user_input.conversation_id or ulid.ulid()
            chat_log = ha_conversation.ChatLog(self.hass, conversation_id)
            
            # Call the internal handler method
            return await self._async_handle_message(user_input, chat_log)
        except Exception as err:
            _LOGGER.error("Error processing conversation: %s", err)
            intent_response = intent.IntentResponse(language=user_input.language)
            intent_response.async_set_error(
                intent.IntentResponseErrorCode.UNKNOWN,
                f"Error processing conversation: {err}",
            )
            return ha_conversation.ConversationResult(
                conversation_id=conversation_id if 'conversation_id' in locals() else ulid.ulid(),
                response=intent_response,
            )

    async def _async_handle_message(
        self,
        user_input: ha_conversation.ConversationInput,
        chat_log: ha_conversation.ChatLog,
    ) -> ha_conversation.ConversationResult:
        """Process a sentence."""
        options = self.entry.options

        try:
            await chat_log.async_update_llm_data(
                DOMAIN,
                user_input,
                options.get(CONF_LLM_HASS_API) if self.control_ha else None,
                self.prompt,
            )
        except ha_conversation.ConverseError as err:
            return err.as_conversation_result()

        tools = None
        if chat_log.llm_api:
            tools = [
                _format_tool(tool, chat_log.llm_api.custom_serializer)
                for tool in chat_log.llm_api.tools
            ]

        model = self.model
        max_tokens = self.max_tokens
        temperature = self.temperature

        if self.recommended_settings:
            model = AnthropicModels.default()
            max_tokens = DEFAULT_MAX_TOKENS
            temperature = DEFAULT_TEMPERATURE
        
        # Дополнительная валидация типов данных перед API вызовом
        # Это защищает от случаев, когда значения могли быть изменены извне
        try:
            max_tokens = int(max_tokens) if max_tokens is not None else DEFAULT_MAX_TOKENS
        except (ValueError, TypeError) as err:
            _LOGGER.warning("Invalid max_tokens value '%s' in API call, using default: %s", max_tokens, err)
            max_tokens = DEFAULT_MAX_TOKENS
            
        try:
            temperature = float(temperature) if temperature is not None else DEFAULT_TEMPERATURE
        except (ValueError, TypeError) as err:
            _LOGGER.warning("Invalid temperature value '%s' in API call, using default: %s", temperature, err)
            temperature = DEFAULT_TEMPERATURE

        # Convert chat log content to Anthropic message format
        messages = [
            m
            for content in chat_log.content
            for m in _convert_content_to_param(content)
        ]
        
        # Ensure we have at least one message (required by Anthropic API)
        if not messages and user_input.text:
            # Add the user's input as a message if no messages exist
            messages.append({
                "role": "user",
                "content": [{"type": "text", "text": user_input.text}]
            })
            _LOGGER.debug("No messages in chat log, adding user input as message: %s", user_input.text)

        # To prevent infinite loops, we limit the number of iterations
        for _iteration in range(MAX_TOOL_ITERATIONS):
            try:
                # Get system prompt with current state information
                system_prompt = await self._get_system_prompt(user_input.language)
                
                # For the first iteration, automatically get home state data
                if _iteration == 0 and chat_log.llm_api:
                    # Find the get_home_state tool if available
                    get_state_tool = None
                    for tool in chat_log.llm_api.tools:
                        if tool.name == "get_home_state":
                            get_state_tool = tool
                            break
                    
                    if get_state_tool:
                        _LOGGER.info("Automatically retrieving current home state")
                        try:
                            tool_input = llm.ToolInput(
                                tool_name="get_home_state",
                                tool_args={},
                            )
                            state_response = await chat_log.llm_api.async_call_tool(tool_input)
                            _LOGGER.debug("Home state response: %s", state_response)
                            
                            # Format the state data in a more readable way
                            formatted_state = self._format_home_state_data(state_response)
                            
                            # Add this information to the system prompt
                            system_prompt += "\n\nCurrent home state data:\n" + formatted_state
                        except Exception as err:
                            _LOGGER.error("Error getting home state: %s", err)
                
                # Log the API request with type information for debugging
                _LOGGER.debug(
                    "Calling Anthropic API with model=%s, max_tokens=%s (type: %s), temperature=%s (type: %s), system=%s, messages=%s, tools=%s",
                    model,
                    max_tokens,
                    type(max_tokens).__name__,
                    temperature,
                    type(temperature).__name__,
                    system_prompt,
                    messages,
                    tools,
                )
                
                # Prepare API call parameters
                api_params = {
                    "model": model,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "system": system_prompt,
                    "messages": messages,
                }
                
                # Only add tools if they are available
                if tools:
                    api_params["tools"] = tools
                
                # Call the create method with the prepared parameters
                response = await self.client.messages.create(**api_params)
                
                # Log the API response
                _LOGGER.debug("Received response from Anthropic API: %s", response)
            except APIError as err:
                _LOGGER.error("Error calling Anthropic API: %s", err)
                intent_response = intent.IntentResponse(language=user_input.language)
                intent_response.async_set_error(
                    intent.IntentResponseErrorCode.UNKNOWN,
                    f"Error calling Anthropic API: {err}",
                )
                return ha_conversation.ConversationResult(
                    conversation_id=chat_log.conversation_id,
                    response=intent_response,
                )

            # Process the response using the chat_log
            async for content in chat_log.async_add_delta_content_stream(
                user_input.agent_id or self.entity_id, _transform_stream(chat_log, response)
            ):
                messages.extend(_convert_content_to_param(content))

            # Check if there are any unresponded tool results in the chat log
            if not chat_log.unresponded_tool_results:
                break

        intent_response = intent.IntentResponse(language=user_input.language)
        if chat_log.content and isinstance(chat_log.content[-1], ha_conversation.AssistantContent):
            final_response = chat_log.content[-1].content or ""
            intent_response.async_set_speech(final_response)
        else:
            # Fallback to extracting text from the response
            response_text = ""
            if hasattr(response, "content") and response.content:
                for content_item in response.content:
                    if hasattr(content_item, "type") and content_item.type == "text":
                        response_text = content_item.text
                        break
                    elif isinstance(content_item, dict) and content_item.get("type") == "text":
                        response_text = content_item.get("text", "")
                        break
            
            intent_response.async_set_speech(response_text)
        
        return ha_conversation.ConversationResult(
            conversation_id=chat_log.conversation_id,
            response=intent_response,
            continue_conversation=chat_log.continue_conversation,
        )

    async def _async_entry_update_listener(
        self, hass: HomeAssistant, entry: ConfigEntry
    ) -> None:
        """Handle options update."""
        # Reload as we update device info + entity name + supported features
        await hass.config_entries.async_reload(entry.entry_id)

    async def _get_system_prompt(self, language: str) -> str:
        """Get the system prompt for the specified language."""
        # Pass the language to _async_generate_prompt to get localized base prompt
        try:
            # Use the template prompt with language support
            prompt = await self._async_generate_prompt(language)
            
            # Add information about Home Assistant entities
            entity_states = self._get_entity_states()
            
            # Load translations for the current language
            translations = await self._get_translations(language)
            
            # Get the entity info header and data instructions from translations
            if "system_prompts.entity_info" in translations and "system_prompts.data_instructions" in translations:
                entity_info_header = translations["system_prompts.entity_info"]
                data_instructions = translations["system_prompts.data_instructions"]
            else:
                # Fall back to English
                english_translations = await self._get_translations("en")
                entity_info_header = english_translations.get(
                    "system_prompts.entity_info",
                    "Here is information about the current state of Home Assistant entities:"
                )
                data_instructions = english_translations.get(
                    "system_prompts.data_instructions",
                    "IMPORTANT: When answering questions about device states, sensor readings, or entity information:\n1. ALWAYS use the most current data provided to you, either from the entity states above or from the 'Current home state data' section if available.\n2. When asked about temperatures, humidity, or other sensor readings, ALWAYS provide the specific values from the data.\n3. Format your responses clearly, listing the specific values for each relevant entity.\n4. If you don't have the requested information in your data, clearly state that you don't have that information."
                )
            
            # Create a template for the entire additional content
            additional_content_template = f"""
{entity_info_header}
{{{{ entity_states }}}}

{data_instructions}
"""
            
            # Render the additional content template
            try:
                tpl = template.Template(additional_content_template, self.hass)
                rendered_additional_content = tpl.render({
                    "entity_states": entity_states
                })
                
                # Add the rendered additional content to the prompt
                return prompt + rendered_additional_content
            except Exception as err:
                _LOGGER.warning("Error rendering additional content template: %s. Using simple format.", err)
                # Fallback to simple format
                return f"{prompt}\n\n{entity_info_header}\n{entity_states}\n\n{data_instructions}"
                
        except Exception as err:
            _LOGGER.warning("Error generating system prompt: %s. Using default prompt.", err)
            return DEFAULT_PROMPT

    def _get_entity_states(self) -> str:
        """Get information about Home Assistant entities."""
        try:
            states = self.hass.states.async_all()
            
            # Filter to only include entities that are exposed to the conversation agent
            exposed_entities = []
            for state in states:
                # Include more domains to provide more comprehensive information
                domain = state.entity_id.split('.')[0]
                if domain in [
                    'sensor', 'binary_sensor', 'light', 'switch', 'climate',
                    'media_player', 'fan', 'cover', 'lock', 'alarm_control_panel',
                    'vacuum', 'camera', 'scene', 'script', 'automation'
                ]:
                    exposed_entities.append(state)
            
            if not exposed_entities:
                return "No entities are currently exposed to the conversation agent."
            
            # Format entity information with more details
            entity_info = []
            
            # Group entities by domain for better organization
            entities_by_domain = {}
            for state in exposed_entities:
                try:
                    domain = state.entity_id.split('.')[0]
                    if domain not in entities_by_domain:
                        entities_by_domain[domain] = []
                    entities_by_domain[domain].append(state)
                except Exception as err:
                    _LOGGER.warning("Error processing entity %s: %s", state.entity_id, err)
            
            # Format each domain's entities
            for domain, entities in entities_by_domain.items():
                entity_info.append(f"\n{domain.upper()} DEVICES:")
                
                for state in entities:
                    try:
                        entity_id = state.entity_id
                        friendly_name = state.attributes.get('friendly_name', entity_id)
                        current_state = state.state
                        
                        # Add more details based on domain
                        details = []
                        
                        # Add common attributes if available
                        if 'unit_of_measurement' in state.attributes:
                            details.append(f"{current_state} {state.attributes['unit_of_measurement']}")
                        elif domain == 'climate':
                            if 'current_temperature' in state.attributes:
                                details.append(f"Current: {state.attributes['current_temperature']}°")
                            if 'temperature' in state.attributes:
                                details.append(f"Set to: {state.attributes['temperature']}°")
                            if 'hvac_action' in state.attributes:
                                details.append(f"Action: {state.attributes['hvac_action']}")
                        elif domain in ['light', 'fan']:
                            if 'brightness' in state.attributes and state.attributes['brightness'] is not None:
                                try:
                                    # Convert brightness (0-255) to percentage
                                    brightness_pct = round(state.attributes['brightness'] / 255 * 100)
                                    details.append(f"Brightness: {brightness_pct}%")
                                except Exception as err:
                                    _LOGGER.warning("Error processing brightness for %s: %s", state.entity_id, err)
                        
                        # Format the line
                        if details:
                            entity_info.append(f"  {friendly_name} ({entity_id}): {current_state} ({', '.join(details)})")
                        else:
                            entity_info.append(f"  {friendly_name} ({entity_id}): {current_state}")
                    except Exception as err:
                        _LOGGER.warning("Error formatting entity %s: %s", state.entity_id, err)
            
            return "\n".join(entity_info)
        except Exception as err:
            _LOGGER.error("Error getting entity states: %s", err)
            return "Error retrieving entity states."

    def _format_home_state_data(self, state_data) -> str:
        """Format home state data in a more readable way."""
        if not state_data or not isinstance(state_data, dict):
            return str(state_data)
            
        # Check if the response has a 'result' field (common format from get_home_state)
        if 'result' in state_data and isinstance(state_data['result'], str):
            # Parse the result if it's a string
            result = state_data['result']
            
            # Format the data to highlight important information
            formatted_lines = []
            
            # Group entities by area for better organization
            entities_by_area = {}
            
            # Process each line
            for line in result.split('\n'):
                line = line.strip()
                if not line:
                    continue
                    
                # Extract area information
                if "areas:" in line:
                    area = line.split("areas:")[1].strip()
                    entity_info = line.split("areas:")[0].strip()
                    
                    if area not in entities_by_area:
                        entities_by_area[area] = []
                    
                    entities_by_area[area].append(entity_info)
                else:
                    # Add lines that don't have area information directly
                    formatted_lines.append(line)
            
            # Format entities by area
            for area, entities in entities_by_area.items():
                formatted_lines.append(f"\n{area.upper()}:")
                for entity in entities:
                    formatted_lines.append(f"  {entity}")
            
            return "\n".join(formatted_lines)
        
        # If the response doesn't have a 'result' field, return it as is
        return str(state_data)

    async def _get_translations(self, language: str) -> dict:
        """Get translations with caching."""
        try:
            if language not in self._translations_cache:
                try:
                    self._translations_cache[language] = await translation.async_get_translations(
                        self.hass, language, "system_prompts", DOMAIN
                    )
                except Exception as err:
                    _LOGGER.warning("Error loading translations for %s: %s", language, err)
                    self._translations_cache[language] = {}
            
            return self._translations_cache[language]
        except Exception as err:
            _LOGGER.error("Error in _get_translations: %s", err)
            return {}
            
    async def _async_generate_prompt(self, language: str = None) -> str:
        """Generate the prompt for the conversation based on language."""
        # If a custom prompt is provided in the config, use that instead
        if self.prompt and self.prompt != DEFAULT_PROMPT:
            return self.prompt
        
        # Get the language from parameter or from Home Assistant config
        if language is None:
            language = self.hass.config.language
        
        try:
            # Load translations for the current language
            translations = await self._get_translations(language)
            
            # Get the base prompt from translations, or fall back to English
            if "system_prompts.base_prompt" in translations:
                prompt_template = translations["system_prompts.base_prompt"]
            else:
                # Fall back to English
                english_translations = await self._get_translations("en")
                prompt_template = english_translations.get(
                    "system_prompts.base_prompt", DEFAULT_PROMPT
                )
        except Exception as err:
            _LOGGER.warning("Error loading translations: %s. Using default prompt.", err)
            prompt_template = DEFAULT_PROMPT
        
        # Apply the template with the current control_ha setting
        try:
            tpl = template.Template(prompt_template, self.hass)
            rendered_prompt = tpl.render({
                "control_ha": self.control_ha
            })
            return rendered_prompt
        except Exception as err:
            _LOGGER.warning("Error rendering prompt template: %s. Using default prompt.", err)
            return DEFAULT_PROMPT