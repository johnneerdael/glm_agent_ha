"""The Llama Query agent implementation."""
import logging
import json
import aiohttp
from typing import Dict, Any, List, Optional
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class LlamaAgent:
    """Agent for handling Llama queries with dynamic data requests."""

    def __init__(self, hass: HomeAssistant, api_key: str):
        """Initialize the agent."""
        self.hass = hass
        self.api_key = api_key
        self.LLAMA_API_URL = "https://api.llama.com/v1/chat/completions"
        self.conversation_history = []
        _LOGGER.debug("LlamaAgent initialized with API URL: %s", self.LLAMA_API_URL)

    async def get_entity_state(self, entity_id: str) -> Dict[str, Any]:
        """Get the state of a specific entity."""
        try:
            _LOGGER.debug("Requesting entity state for: %s", entity_id)
            state = self.hass.states.get(entity_id)
            if not state:
                _LOGGER.warning("Entity not found: %s", entity_id)
                return {"error": f"Entity {entity_id} not found"}
            
            result = {
                "entity_id": state.entity_id,
                "state": state.state,
                "last_changed": state.last_changed.isoformat() if state.last_changed else None,
                "friendly_name": state.attributes.get("friendly_name"),
                "attributes": {k: (v.isoformat() if hasattr(v, 'isoformat') else v) 
                             for k, v in state.attributes.items()}
            }
            _LOGGER.debug("Retrieved entity state: %s", json.dumps(result))
            return result
        except Exception as e:
            _LOGGER.exception("Error getting entity state: %s", str(e))
            return {"error": f"Error getting entity state: {str(e)}"}

    async def get_entities_by_domain(self, domain: str) -> List[Dict[str, Any]]:
        """Get all entities for a specific domain."""
        try:
            _LOGGER.debug("Requesting all entities for domain: %s", domain)
            states = [state for state in self.hass.states.async_all() 
                     if state.entity_id.startswith(f"{domain}.")]
            _LOGGER.debug("Found %d entities in domain %s", len(states), domain)
            return [await self.get_entity_state(state.entity_id) for state in states]
        except Exception as e:
            _LOGGER.exception("Error getting entities by domain: %s", str(e))
            return [{"error": f"Error getting entities for domain {domain}: {str(e)}"}]

    async def get_calendar_events(self, entity_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get calendar events, optionally filtered by entity_id."""
        try:
            if entity_id:
                _LOGGER.debug("Requesting calendar events for specific entity: %s", entity_id)
                return [await self.get_entity_state(entity_id)]
            
            _LOGGER.debug("Requesting all calendar events")
            return await self.get_entities_by_domain("calendar")
        except Exception as e:
            _LOGGER.exception("Error getting calendar events: %s", str(e))
            return [{"error": f"Error getting calendar events: {str(e)}"}]

    async def get_automations(self) -> List[Dict[str, Any]]:
        """Get all automations."""
        try:
            _LOGGER.debug("Requesting all automations")
            return await self.get_entities_by_domain("automation")
        except Exception as e:
            _LOGGER.exception("Error getting automations: %s", str(e))
            return [{"error": f"Error getting automations: {str(e)}"}]

    async def get_weather_data(self) -> Dict[str, Any]:
        """Get current weather data."""
        try:
            _LOGGER.debug("Requesting weather data")
            weather_entity = self.hass.states.get("weather.home")
            if not weather_entity:
                _LOGGER.warning("Weather entity not found")
                return {"error": "Weather entity not found"}
            return await self.get_entity_state("weather.home")
        except Exception as e:
            _LOGGER.exception("Error getting weather data: %s", str(e))
            return {"error": f"Error getting weather data: {str(e)}"}

    async def process_query(self, user_query: str) -> Dict[str, Any]:
        """Process a user query and handle data requests."""
        try:
            _LOGGER.debug("Processing new query: %s", user_query)
            
            # Initial system message explaining available data types
            system_message = {
                "role": "system",
                "content": """You are an AI assistant integrated with Home Assistant. 
                You can request specific data by using these commands:
                - get_entity_state(entity_id): Get state of a specific entity
                - get_entities_by_domain(domain): Get all entities in a domain
                - get_calendar_events(entity_id?): Get calendar events
                - get_automations(): Get all automations
                - get_weather_data(): Get current weather data
                
                IMPORTANT: You must ALWAYS respond with a valid JSON object. Do not include any text before or after the JSON.
                When you need data, respond with this exact JSON format:
                {
                    "request_type": "data_request",
                    "request": "command_name",
                    "parameters": {...}
                }
                
                When you have all the data you need, respond with this exact JSON format:
                {
                    "request_type": "final_response",
                    "response": "your answer to the user"
                }
                
                DO NOT include any text before or after the JSON object. The response must be a single, valid JSON object.
                DO NOT include any special characters or formatting in your response."""
            }

            # Add system message to conversation if it's the first message
            if not self.conversation_history:
                _LOGGER.debug("Adding system message to new conversation")
                self.conversation_history.append(system_message)

            # Add user query to conversation
            self.conversation_history.append({
                "role": "user",
                "content": user_query
            })
            _LOGGER.debug("Added user query to conversation history")

            max_iterations = 5  # Prevent infinite loops
            iteration = 0

            while iteration < max_iterations:
                iteration += 1
                _LOGGER.debug(f"Processing iteration {iteration} of {max_iterations}")
                
                try:
                    # Get AI response
                    _LOGGER.debug("Requesting response from Llama API")
                    response = await self._get_llama_response()
                    _LOGGER.debug("Received response from Llama API: %s", response)
                    
                    try:
                        # Try to parse the response as JSON
                        response_data = json.loads(response)
                        _LOGGER.debug("Parsed response data: %s", json.dumps(response_data))
                        
                        if response_data.get("request_type") == "data_request":
                            # Handle data request
                            request_type = response_data.get("request")
                            parameters = response_data.get("parameters", {})
                            _LOGGER.debug("Processing data request: %s with parameters: %s", 
                                        request_type, json.dumps(parameters))
                            
                            # Add AI's response to conversation history
                            self.conversation_history.append({
                                "role": "assistant",
                                "content": response
                            })
                            
                            # Get requested data
                            if request_type == "get_entity_state":
                                data = await self.get_entity_state(parameters.get("entity_id"))
                            elif request_type == "get_entities_by_domain":
                                data = await self.get_entities_by_domain(parameters.get("domain"))
                            elif request_type == "get_calendar_events":
                                data = await self.get_calendar_events(parameters.get("entity_id"))
                            elif request_type == "get_automations":
                                data = await self.get_automations()
                            elif request_type == "get_weather_data":
                                data = await self.get_weather_data()
                            else:
                                data = {"error": f"Unknown request type: {request_type}"}
                                _LOGGER.warning("Unknown request type: %s", request_type)
                            
                            # Check if any data request resulted in an error
                            if isinstance(data, dict) and "error" in data:
                                return {
                                    "success": False,
                                    "error": data["error"]
                                }
                            elif isinstance(data, list) and any("error" in item for item in data):
                                errors = [item["error"] for item in data if "error" in item]
                                return {
                                    "success": False,
                                    "error": "; ".join(errors)
                                }
                            
                            _LOGGER.debug("Retrieved data for request: %s", json.dumps(data))
                            
                            # Add data to conversation as a system message
                            self.conversation_history.append({
                                "role": "system",
                                "content": json.dumps({"data": data})
                            })
                            continue
                        
                        elif response_data.get("request_type") == "final_response":
                            # Add final response to conversation history
                            self.conversation_history.append({
                                "role": "assistant",
                                "content": response
                            })
                            
                            # Return final response
                            _LOGGER.debug("Received final response: %s", response_data.get("response"))
                            return {
                                "success": True,
                                "answer": response_data.get("response", "")
                            }
                        else:
                            _LOGGER.warning("Unknown response type: %s", response_data.get("request_type"))
                            return {
                                "success": False,
                                "error": f"Unknown response type: {response_data.get('request_type')}"
                            }
                            
                    except json.JSONDecodeError as e:
                        _LOGGER.warning("Failed to parse response as JSON: %s", str(e))
                        # If response is not valid JSON, return it as final response
                        return {
                            "success": True,
                            "answer": response
                        }
                        
                except Exception as e:
                    _LOGGER.exception("Error processing AI response: %s", str(e))
                    return {
                        "success": False,
                        "error": f"Error processing AI response: {str(e)}"
                    }

            # If we've reached max iterations without a final response
            _LOGGER.warning("Reached maximum iterations without final response")
            return {
                "success": False,
                "error": "Maximum iterations reached without final response"
            }
            
        except Exception as e:
            _LOGGER.exception("Error in process_query: %s", str(e))
            return {
                "success": False,
                "error": f"Error in process_query: {str(e)}"
            }

    async def _get_llama_response(self) -> str:
        """Get response from Llama API."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "Llama-4-Maverick-17B-128E-Instruct-FP8",
            "messages": self.conversation_history,
            "max_tokens": 2048
        }

        _LOGGER.debug("Sending request to Llama API with payload: %s", 
                     json.dumps(payload, default=str))

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(self.LLAMA_API_URL, headers=headers, json=payload) as resp:
                    if resp.status != 200:
                        error_msg = f"API error {resp.status}: {await resp.text()}"
                        _LOGGER.error("Llama API error: %s", error_msg)
                        raise Exception(error_msg)

                    data = await resp.json()
                    _LOGGER.debug("Received raw response from Llama API: %s", 
                                json.dumps(data, default=str))
                    
                    # Extract the actual response from the API response
                    if 'completion_message' in data:
                        completion = data['completion_message']
                        if isinstance(completion, dict) and 'content' in completion:
                            content = completion['content']
                            if isinstance(content, dict) and 'text' in content:
                                response = content['text']
                                _LOGGER.debug("Extracted text response: %s", response)
                                
                                # Clean up the response
                                # Remove any text before the first {
                                json_start = response.find('{')
                                if json_start >= 0:
                                    response = response[json_start:]
                                    
                                    # Remove any text after the last }
                                    json_end = response.rfind('}')
                                    if json_end >= 0:
                                        response = response[:json_end + 1]
                                        
                                        # Try to parse as JSON to validate
                                        try:
                                            json.loads(response)
                                            _LOGGER.debug("Cleaned and validated JSON response: %s", response)
                                            return response
                                        except json.JSONDecodeError:
                                            _LOGGER.warning("Failed to parse cleaned response as JSON: %s", response)
                                
                                # If we couldn't extract valid JSON, return the raw response
                                _LOGGER.warning("Could not extract valid JSON, returning raw response")
                                return response
                    
                    _LOGGER.warning("No valid response found in API response")
                    raise Exception("No valid response found in API response")
                    
            except aiohttp.ClientError as e:
                _LOGGER.exception("Network error while querying Llama API: %s", str(e))
                raise Exception(f"Network error: {str(e)}")
            except Exception as e:
                _LOGGER.exception("Exception while querying Llama API: %s", str(e))
                raise 