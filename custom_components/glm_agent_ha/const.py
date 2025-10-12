"""Constants for the GLM Coding Plan Agent HA integration."""

DOMAIN = "glm_agent_ha"
CONF_API_KEY = "api_key"
CONF_WEATHER_ENTITY = "weather_entity"

# AI Provider configuration keys
CONF_OPENAI_TOKEN = "openai_token"  # nosec B105
CONF_ANTHROPIC_TOKEN = "anthropic_token"  # nosec B105

# Available AI providers
AI_PROVIDERS = ["openai", "anthropic"]

# AI Provider constants
CONF_MODELS = "models"

# Supported AI providers
DEFAULT_AI_PROVIDER = "openai"
