# GLM Agent HA

A powerful Home Assistant custom integration that connects your Home Assistant instance with the GLM Coding Plan OpenAI endpoint to translate user requests into valid Home Assistant operations, including creating automations automatically!

## 🚀 Quick Install

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=johnneerdael&repository=glm_agent_ha&category=integration)

Click the button above to install GLM Agent HA directly through HACS, or see the [detailed installation instructions](#-installation) below.

## ✨ Features

- 🤖 **GLM Coding Plan Integration**: Seamless integration with GLM Coding Plan OpenAI endpoint
- 🎯 **Model Selection**: Choose from predefined models or use custom model names
- 🏠 **Smart Home Control**: Turn lights on/off, control climate, and manage devices
- ⚡ **Automation Creation**: Automatically create automations based on natural language
- 📋 **Dashboard Creation**: Create and customize Home Assistant dashboards through natural language
- 📊 **Data Access**: Get entity states, history, weather, and more
- 🔒 **Secure**: API keys stored securely in Home Assistant
- 🎨 **Beautiful UI**: Clean, modern chat interface
- 🧠 **Context-Aware AI**: New context services provide a deeper understanding of your Home Assistant environment, enabling more intelligent and accurate responses.
- 🔄 **Real-time**: Instant responses and updates

## 📸 Screenshots

### Automation Creation
![GLM Agent HA Automation Creation](image/Screenshot2.png)

## 📋 Dashboard Creation

GLM Agent HA now supports creating and managing Home Assistant dashboards through natural language conversations! Simply describe what you want, and the AI will create a complete dashboard for you.

### How Dashboard Creation Works

1. **Natural Language Request**: Ask the AI to create a dashboard for any purpose
2. **Entity Discovery**: The AI automatically finds relevant entities in your Home Assistant
3. **Smart Organization**: Entities are organized by room, functionality, or domain
4. **Dashboard Generation**: Complete dashboard with proper cards and layout is created
5. **Integration**: Dashboard is automatically added to your Home Assistant sidebar
6. **Restart Required**: You'll need to restart Home Assistant to see the new dashboard in your sidebar

### Dashboard Creation Examples

#### Simple Room Dashboard
```
"Create a dashboard for my living room lights"
```
The AI will find all living room light entities and create a dashboard with appropriate light control cards.

#### Security Dashboard
```
"Create a security dashboard with all door sensors, cameras, and alarm controls"
```
The AI will create a comprehensive security monitoring dashboard with sensor states, camera feeds, and alarm controls. After creation, restart Home Assistant to see the new dashboard in your sidebar.

#### Energy Monitoring Dashboard
```
"I want an energy dashboard showing power consumption and usage graphs"
```
The AI will create an energy monitoring dashboard with real-time power gauges, usage graphs, and cost tracking.

#### Climate Control Dashboard
```
"Create a climate dashboard for temperature control throughout the house"
```
The AI will organize thermostats, temperature sensors, and HVAC controls in a logical layout.

### Supported Dashboard Features

- **Smart Card Selection**: Appropriate card types for each entity (lights, sensors, media players, etc.)
- **Room-Based Organization**: Entities automatically grouped by area when possible
- **Interactive Clarification**: AI asks follow-up questions to refine your requirements
- **Template-Based Creation**: Built-in templates for common dashboard types (security, energy, climate, etc.)
- **Dynamic Layout**: Optimized card arrangements and view organization
- **Icon Integration**: Automatic Material Design icon selection

### Dashboard Types the AI Can Create

- **Room-Specific**: Living room, bedroom, kitchen, etc.
- **Functional**: Security, energy, climate, media, lighting
- **Device-Specific**: All lights, all sensors, all switches
- **Scenario-Based**: Morning routine, evening security, vacation mode
- **Custom**: Any combination based on your specific needs

For detailed dashboard creation documentation, see: [Dashboard Creation Guide](docs/DASHBOARD_CREATION.md)

## 🚀 Supported AI Provider

### GLM Coding Plan OpenAI Endpoint
- **Models**: GLM Coding Plan optimized models
- **Setup**: Get API key from your GLM Coding Plan subscription
- **Benefits**:
  - Optimized for Home Assistant integration
  - Enhanced automation and dashboard creation capabilities
  - Reliable and consistent performance

## 📦 Installation

### HACS Installation (Recommended)

Use the [Quick Install button](#-quick-install) at the top of this README for the easiest installation, or manually add the repository:

1. Open HACS in your Home Assistant instance
2. Click on "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository: `https://github.com/johnneerdael/glm_agent_ha`
6. Select "Integration" as the category
7. Click "Add"
8. Find "GLM Agent HA" in the integration list
9. Click "Download"
10. Restart Home Assistant
11. Go to Settings → Devices & Services → Add Integration
12. Search for "GLM Agent HA"
13. Follow the setup wizard to configure the GLM Coding Plan OpenAI endpoint

### Manual Installation

1. Download the latest release from the [releases page](https://github.com/johnneerdael/glm_agent_ha/releases)
2. Extract the files
3. Copy the `custom_components/glm_agent_ha` folder to your Home Assistant `custom_components` directory
4. Restart Home Assistant
5. Go to Settings → Devices & Services → Add Integration
6. Search for "GLM Agent HA"
7. Follow the setup wizard to configure the GLM Coding Plan OpenAI endpoint

## ⚙️ Configuration

The integration uses a simple configuration process:

### Configuration Steps
Enter your GLM Coding Plan credentials:
- **API Key**: Your GLM Coding Plan API key
- **Model**: Select from available GLM Coding Plan models

### Configuration Examples

```yaml
# Example configuration.yaml (optional - integration supports config flow only)
glm_agent_ha:
  ai_provider: openai
  glm_coding_plan_api_key: "your-glm-coding-plan-api-key"
  models:
    glm_coding_plan: GLM-4.5-air"
```

## 🎮 Usage

### Chat Interface
Access the beautiful chat interface at:
- **Sidebar**: GLM Agent HA panel
- **URL**: `http://your-ha-instance:8123/glm_agent_ha`



## 🔧 Advanced Features

### Custom Models
Enter any GLM Coding Plan model name in the "Custom Model" field:
- GLM Coding Plan: Enter your preferred GLM Coding Plan model identifier

### Automation Creation
The AI can create automations automatically:
1. Ask: "Create an automation to turn on lights at sunset"
2. Review the generated automation
3. Approve or reject the suggestion
4. Automation is added to your Home Assistant

### Dashboard Creation
The AI can create custom dashboards through conversation:
1. Ask: "Create a security dashboard with cameras and sensors"
2. AI discovers relevant entities and asks clarifying questions
3. Dashboard is generated with appropriate cards and layout
4. Dashboard is automatically added to your Home Assistant sidebar
5. Restart Home Assistant to see the new dashboard

### Data Access
The AI can access comprehensive Home Assistant data:
- Entity states and history
- Weather information
- Person locations
- Device registry
- Area/room information
- Statistics and analytics

## 🛠️ Development

### Contributing
We welcome contributions from the community! Whether you're fixing bugs, adding features, or improving documentation, your help is appreciated.

Please check out our [contribution guidelines](CONTRIBUTING.md) for detailed information on how to contribute to this project.

#### Quick Start
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

For security issues, please review our [security policy](SECURITY.md).

### CI/CD Workflows

This project uses GitHub Actions to ensure code quality and reliability:

- **Quality Checks**: Runs all checks in a single workflow (Python 3.12)
- **Python Linting**: Checks code style with flake8, black, and isort
- **Python Type Checking**: Verifies typing with mypy (Python 3.12 compatibility)
- **Python Tests**: Runs tests with pytest (Python 3.12)
- **Security Scan**: Checks for security vulnerabilities with Bandit
- **Home Assistant Validation**: Validates the integration with hassfest
- **HACS Validation**: Ensures compatibility with HACS

All workflows run automatically on push and pull requests using Python 3.12 to ensure compatibility with the latest Home Assistant versions. You can also run them manually via the "Actions" tab in the GitHub repository.

### API Structure
The integration provides these main components:
- **AI Client**: GLM Coding Plan OpenAI endpoint integration
- **Agent**: Core logic for processing requests
- **Config Flow**: Setup and options management
- **Frontend**: Chat interface
- **Dashboard Templates**: Templates for dashboard creation
- **Context Services**:
  - `AreaTopologyService`: Builds a topological map of your home's areas.
  - `EntityRelationshipService`: Maps relationships between entities, devices, and areas.
  - `ContextCacheManager`: Improves performance by caching contextual data.

## 📋 Requirements

- Home Assistant 2023.3+
- **Python 3.12+** (required for compatibility with Home Assistant 2025.1.x+)
- GLM Coding Plan API key

### Python Version Note

**Important**: Starting with version 0.99.3, this integration requires Python 3.12 or later. This change was made to ensure compatibility with Home Assistant 2025.1.x and later versions, which use syntax features only available in Python 3.12+.

If you're running an older Home Assistant version with Python 3.11, please use version 0.99.2 or earlier of this integration.

## 🔒 Security

- API keys are stored securely in Home Assistant's encrypted storage
- All communication uses HTTPS
- No data is stored outside your Home Assistant instance
- Provider-specific security practices are followed

## ☕ Support the Project

If you find this integration helpful and would like to support its development, you can buy me a coffee! Your support helps keep this project active and maintained.

[![Buy Me A Coffee](https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg)](https://www.buymeacoffee.com/johnneerdael)

Every contribution, no matter how small, is greatly appreciated and helps fund the continued development and improvement of GLM Agent HA.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/johnneerdael/glm_agent_ha/issues)
- **Discussions**: [GitHub Discussions](https://github.com/johnneerdael/glm_agent_ha/discussions)
- **Documentation**: [Wiki](https://github.com/johnneerdael/glm_agent_ha/wiki)

## 🙏 Acknowledgments

- Home Assistant community for the excellent platform
- GLM Coding Plan for the powerful API endpoint
- Special thanks to @RmG152 for their valuable help with development
- Contributors and testers who help improve this integration

---

**Made with ❤️ for the Home Assistant community**
