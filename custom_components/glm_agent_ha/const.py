"""Constants for the GLM Coding Plan Agent HA integration."""

DOMAIN = "glm_agent_ha"
CONF_API_KEY = "api_key"
CONF_WEATHER_ENTITY = "weather_entity"

# AI Provider configuration keys
CONF_OPENAI_TOKEN = "openai_token"  # nosec B105

# Available AI providers
AI_PROVIDERS = ["openai",]

# AI Provider constants
CONF_MODELS = "models"

# Supported AI providers
DEFAULT_AI_PROVIDER = "openai"

# Context cache defaults
DEFAULT_CACHE_TTL = 300  # seconds
DEFAULT_CACHE_MAX_SIZE = 1000

# Configuration keys for context features
CONF_CACHE_TTL = "cache_ttl"
CONF_CACHE_TIMEOUT = "cache_timeout"
CONF_ENABLE_DIAGNOSTICS = "enable_diagnostics"
CONF_ENABLE_ENERGY = "enable_energy"
CONF_ENABLE_AREA_TOPOLOGY = "enable_area_topology"
CONF_ENABLE_ENTITY_TYPE_CACHE = "enable_entity_type_cache"
CONF_ENABLE_ENTITY_RELATIONSHIPS = "enable_entity_relationships"

# Plan configuration
CONF_PLAN = "plan"

# Available plans
PLAN_LITE = "lite"
PLAN_PRO = "pro"
PLAN_MAX = "max"

DEFAULT_PLAN = PLAN_LITE

# MCP Server configuration
CONF_MCP_SERVERS = "mcp_servers"
CONF_ENABLE_MCP_INTEGRATION = "enable_mcp_integration"

# AI Task Entity configuration
CONF_ENABLE_AI_TASK = "enable_ai_task"
CONF_ENABLE_CONVERSATION = "enable_conversation"

# LLM API configuration
CONF_LLM_HASS_API = "llm_hass_api"
CONF_PROMPT = "prompt"

# Media hosting configuration
CONF_HA_BASE_URL = "ha_base_url"

# Entity configuration
CONF_AI_PROVIDER = "ai_provider"
