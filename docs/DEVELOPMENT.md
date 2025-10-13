
# Development Guide for AI Agent HA

This guide provides information about the development workflow and technical aspects of the AI Agent HA project.

## Development Environment Setup

### Prerequisites

- Python 3.11+
- Git
- Home Assistant development environment
- API keys for GLM Coding Plan from Z.AI

### Setting Up a Development Environment

1. **Fork and clone the repository**:
   ```bash
   git clone https://github.com/johnneerdael/glm_agent_ha.git
   cd glm_agent_ha
   ```

2. **Set up a Home Assistant development environment**:
   - Option 1: Use a dedicated Home Assistant development instance
   - Option 2: Use a test Home Assistant container
   - Option 3: Use Home Assistant Core in development mode

   For details on setting up a Home Assistant development environment, see the [Home Assistant Developer Documentation](https://developers.home-assistant.io/docs/development_environment).

3. **Install the integration in development mode**:
   - Symlink or copy the `custom_components/glm_agent_ha` folder to your Home Assistant `custom_components` directory
   - Restart Home Assistant
   - Add the integration through the Home Assistant UI

## Project Architecture

### Core Components

- **__init__.py**: Integration initialization and setup
- **agent.py**: Core AI agent logic and AI provider integration
- **config_flow.py**: Configuration flow UI and logic
- **const.py**: Constants and configuration options
- **dashboard_templates.py**: Templates for dashboard creation
- **frontend/**: Frontend UI components
- **services.yaml**: Service definitions
- **translations/**: Localization files

### Context Services

To enhance the agent's environmental awareness, a dedicated context services layer has been introduced. These services run in the background to build a rich, structured understanding of the Home Assistant environment. This data is then injected into the AI's context, allowing for more accurate and intelligent responses.

#### How it Works

1.  **Data Collection**: The services periodically fetch data from Home Assistant's area, device, and entity registries.
2.  **Caching**: The raw data is stored in the `ContextCacheManager` to avoid redundant lookups and reduce the load on Home Assistant.
3.  **Data Modeling**: The `AreaTopologyService` and `EntityRelationshipService` process the cached data, building structured Pydantic models that represent the home's layout and relationships.
4.  **Context Injection**: When the agent receives a prompt, it queries these services to retrieve relevant contextual information, which is then passed to the AI model.

- **context/cache.py**: Implements the `ContextCacheManager`, a simple in-memory cache to store the results of context-gathering operations. This reduces redundant lookups and improves performance.
- **context/area_topology.py**: Contains the `AreaTopologyService`, which discovers and maps the physical layout of the home by analyzing Home Assistant Areas and their relationships.
- **context/entity_relationships.py**: Contains the `EntityRelationshipService`, which discovers and maps the connections between entities, devices, and areas, creating a comprehensive graph of the environment.

#### ContextCacheManager

The `ContextCacheManager` is a foundational service that provides an in-memory caching layer for Home Assistant's registries. It is designed to minimize redundant data lookups and improve the overall performance of the agent.

**Key Features**:
- **Time-to-Live (TTL) Caching**: Stores registry data for a configurable duration, ensuring a balance between performance and data freshness.
- **Automatic Invalidation**: Listens for Home Assistant's `EVENT_REGISTRY_UPDATED` and clears the relevant cache, ensuring that the agent always has access to up-to-date information.
- **Asynchronous by Design**: All cache operations are asynchronous to prevent blocking Home Assistant's event loop.
- **Graceful Shutdown**: Clears all caches when Home Assistant stops to ensure a clean state on restart.

#### AreaTopologyService

The `AreaTopologyService` builds a structured understanding of the physical layout of the user's home. It analyzes areas, floors, and the entities and devices within them to create a comprehensive topological map.

**Key Methods**:
- `get_floor_summary()`: Returns a high-level summary of all floors, including the areas and number of entities on each. This is useful for getting a quick overview of the home's structure.
- `get_area_topology(area_id)`: Provides a detailed, structured breakdown of a specific area, including its associated entities and devices.
- `get_entities_by_filter(...)`: Allows for advanced, server-side filtering of entities based on criteria like domain, device class, area, and floor.

#### EntityRelationshipService

The `EntityRelationshipService` is responsible for discovering and mapping the complex relationships between entities, devices, and areas. It creates a rich graph of the environment that allows the agent to make more intelligent inferences about how different parts of the smart home are connected.

**Key Features**:
- **Relationship Graph**: Builds and caches a graph of device-to-entity and area-to-device relationships, enabling fast lookups of related components.
- **Intelligent Categorization**: Groups entities into logical, human-readable categories (e.g., "lighting," "security," "climate") based on their domain and device class.
- **Advanced Discovery Methods**: Provides methods to find related entities, discover entities by category, and perform attribute-based searches, giving the agent powerful tools for environmental analysis.
 
 ### Data Flow
 
 1. **User Input**: User provides a natural language request
2. **Agent Processing**:
   - Context collection (entities, states, etc.)
   - AI provider query
   - Response parsing and validation
3. **Action Execution**:
   - Service calls
   - Entity control
   - Automation/dashboard creation
4. **Response Delivery**: Results returned to user

## Development Workflow

### Adding a New Feature

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Implement your changes**:
   - Follow the coding standards in CONTRIBUTING.md
   - Add appropriate docstrings and comments
   - Update relevant documentation

3. **Test your changes**:
   - Test with multiple AI providers if applicable
   - Test with various user inputs
   - Check for edge cases and error handling

4. **Submit a pull request**:
   - Push your branch to your fork
   - Create a PR to the main repository
   - Fill out the PR template completely

### Adding Support for a New AI Provider

1. **Create a new client class** in `agent.py`:
   ```python
   class NewProviderClient:
       """Client for New AI Provider."""
       
       def __init__(self, api_key: str, model: str):
           """Initialize the client."""
           self.api_key = api_key
           self.model = model
           # Additional setup
           
       async def query(self, prompt: str, context: dict) -> str:
           """Send a query to the AI provider.
           
           Args:
               prompt: The user's prompt
               context: The context dictionary with Home Assistant data
               
           Returns:
               The AI provider's response
           """
           # Implementation here
   ```

2. **Add provider configuration** to `config_flow.py`:
   - Add provider option in the config flow
   - Create appropriate config fields
   - Add validation for the new provider's API key and models

3. **Update constants** in `const.py`:
   - Add provider name constant
   - Add default models list
   - Add any provider-specific configuration options

4. **Update documentation**:
   - Add provider setup instructions to README.md
   - Update configuration examples

### Frontend Development

1. **Understand the existing frontend**:
   - Examine `frontend/glm_agent_ha-panel.js`
   - Note Home Assistant frontend patterns

2. **Make frontend changes**:
   - Follow Home Assistant frontend guidelines
   - Test on multiple browsers and screen sizes
   - Ensure accessibility compliance

3. **Test frontend changes**:
   - Verify real-time updates
   - Check responsive design
   - Test with various AI responses

## Testing

### Manual Testing

Test the following scenarios:
- Light control: "Turn on the living room lights"
- Climate control: "Set the thermostat to 72 degrees"
- Entity state queries: "What's the temperature in the bedroom?"
- Automation creation: "Create an automation to turn off lights at 11 PM"
- Dashboard creation: "Create a security dashboard"
- Error handling: Test with invalid entities or requests
- Configuration flow: Test setup and options flow

### Debug Logs

Enable debug logging in Home Assistant:
```yaml
logger:
  default: info
  logs:
    custom_components.glm_agent_ha: debug
```

Check the Home Assistant logs at `<config_dir>/home-assistant.log` or in the "Logs" section of the Home Assistant UI.

## Common Development Tasks

### Adding a New Command Pattern

To add support for a new command pattern (e.g., a new type of automation):

1. **Identify the command pattern** in user prompts
2. **Update the AI prompt templates** with examples
3. **Add handling code** in the agent logic
4. **Test thoroughly** with various phrasings

### Adding a New Dashboard Template

To add a new dashboard template:

1. **Create the template** in `dashboard_templates.py`
2. **Design for flexibility** (avoid hardcoded entity IDs)
3. **Add documentation** for the template
4. **Test with different entity configurations**

### Troubleshooting Development Issues

- **Configuration not showing up**: Restart Home Assistant and clear browser cache
- **API key validation errors**: Verify API key format and permissions
- **Frontend not updating**: Check for JavaScript errors in browser console
- **Agent not responding**: Check debug logs for connection issues

### Configuring Context Services

The new context services can be configured from the integration's options menu in the Home Assistant UI. These settings allow you to enable or disable specific features and fine-tune their behavior.

- **Enable Area Topology Service**: Activates the `AreaTopologyService`. When enabled, the agent gains a deep understanding of your home's physical layout, including floors and areas. This allows the agent to answer questions like, "How many lights are on the ground floor?"
- **Enable Entity Relationships Service**: Activates the `EntityRelationshipService`. This allows the agent to understand the connections between your devices and entities, enabling more complex commands like, "Turn off all media players in the living room."
- **Context Cache TTL**: Sets the time-to-live (in seconds) for the context cache. A lower value means the agent will have more up-to-date information, but may result in slightly slower responses. A higher value can improve performance but may lead to the agent using stale data.

These options can be found under the "Advanced Options" section of the integration's configuration.

### Testing Context Services

The context services are designed to be tested independently. The test suite includes dedicated files for each service:
- `tests/test_ai_agent_ha/test_cache.py`
- `tests/test_ai_agent_ha/test_area_topology.py`
- `tests/test_ai_agent_ha/test_entity_relationships.py`

To run the tests, use `pytest`:
```bash
pytest tests/test_ai_agent_ha/
```

When writing tests for these services, make use of the provided fixtures to mock `HomeAssistant` and the various registries.
 
 ## Release Process
 
 1. **Update version number** in `manifest.json`
2. **Update CHANGELOG.md** with notable changes
3. **Create a release** on GitHub
4. **Tag the release** with the version number

## Additional Resources

- [Home Assistant Developer Documentation](https://developers.home-assistant.io/)
- [Home Assistant Custom Component Development](https://developers.home-assistant.io/docs/creating_component_index)
- [Home Assistant Frontend Development](https://developers.home-assistant.io/docs/frontend/custom-ui/)
- [AI Provider Documentation]:
  - [GLM Coding Plan API](https://docs.z.ai/devpack/overview)

## Getting Help

If you encounter issues during development:
- Check the [GitHub Discussions](https://github.com/johnneerdael/glm_agent_ha/discussions)
- Review existing issues and pull requests
- Ask questions in the discussions area

---

Happy coding! 🚀 