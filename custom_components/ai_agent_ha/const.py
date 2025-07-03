"""Constants for the AI Agent HA integration."""

DOMAIN = "ai_agent_ha"
CONF_API_KEY = "api_key"
CONF_WEATHER_ENTITY = "weather_entity"

# AI Provider configuration keys
CONF_LLAMA_TOKEN = "llama_token"
CONF_OPENAI_TOKEN = "openai_token"
CONF_GEMINI_TOKEN = "gemini_token"
CONF_OPENROUTER_TOKEN = "openrouter_token"
CONF_ANTHROPIC_TOKEN = "anthropic_token"
CONF_LOCAL_URL = "local_url"
CONF_LOCAL_MODEL = "local_model"

# Available AI providers
AI_PROVIDERS = ["llama", "openai", "gemini", "openrouter", "anthropic", "local"]

# AI Provider constants
CONF_MODELS = "models"

# Supported AI providers
DEFAULT_AI_PROVIDER = "openai"
