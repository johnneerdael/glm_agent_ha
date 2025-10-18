"""Constants for the Anthropic integration."""
from enum import StrEnum

DOMAIN = "anthropic"
CONF_API_KEY = "api_key"
CONF_PROMPT = "prompt"
CONF_CHAT_MODEL = "chat_model"
CONF_MAX_TOKENS = "max_tokens"
CONF_TEMPERATURE = "temperature"
CONF_RECOMMENDED_SETTINGS = "recommended_settings"
CONF_CONTROL_HA = "control_ha"

DEFAULT_PROMPT = """You are Claude, a helpful AI assistant integrated with Home Assistant. You are running inside a Home Assistant instance.
{%- if control_ha %}

You have access to the user's home automation devices and sensors. You can control devices and provide information about the state of sensors. When the user asks you to control a device or asks about the state of a device, use the appropriate Home Assistant API to fulfill the request, but don't describe the process of performing the action. If a device is unavailable, simply state that it's unavailable without explaining why.

Examples of good responses:
- When asked "What's the temperature in the living room?": "The living room is 72 degrees."
- When commanded "Turn on the bedroom light": "Bedroom light turned on."
- When commanded "Turn off the kitchen air conditioner": "Kitchen air conditioner turned off."
- When commanded "Turn on the TV in the kids room" (if unavailable): "The TV in the kids room is unavailable."
{%- endif %}

Give only specific results of queries or actions without describing the process of performing them. Don't use phrases like "I checked...", "I performed...", "I turned on...", "I sent a command..." or "For this I need to check...". Answer concisely, only addressing the substance of the request.
"""

DEFAULT_MAX_TOKENS = 4096
DEFAULT_TEMPERATURE = 0.7
DEFAULT_CONTROL_HA = True
DEFAULT_RECOMMENDED_SETTINGS = True


class AnthropicModels(StrEnum):
    """Anthropic models."""

    # Claude 4 models
    CLAUDE_OPUS_4 = "claude-opus-4-20250514"
    CLAUDE_SONNET_4 = "claude-sonnet-4-20250514"
    
    # Claude 3.7 models
    CLAUDE_3_7_SONNET = "claude-3-7-sonnet-20250219"
    
    # Claude 3.5 models (updated versions)
    CLAUDE_3_5_SONNET = "claude-3-5-sonnet-20241022"
    CLAUDE_3_5_HAIKU = "claude-3-5-haiku-20241022"
    
    # Legacy Claude 3.5 models
    CLAUDE_3_5_SONNET_LEGACY = "claude-3-5-sonnet-20240620"
    
    # Claude 3 models
    CLAUDE_3_OPUS = "claude-3-opus-20240229"
    CLAUDE_3_SONNET = "claude-3-sonnet-20240229"
    CLAUDE_3_HAIKU = "claude-3-haiku-20240307"

    @classmethod
    def default(cls) -> "AnthropicModels":
        """Return the default model."""
        return cls.CLAUDE_SONNET_4


ANTHROPIC_MODELS = [
    # Latest Claude 4 models
    AnthropicModels.CLAUDE_OPUS_4,
    AnthropicModels.CLAUDE_SONNET_4,
    
    # Claude 3.7 models
    AnthropicModels.CLAUDE_3_7_SONNET,
    
    # Updated Claude 3.5 models
    AnthropicModels.CLAUDE_3_5_SONNET,
    AnthropicModels.CLAUDE_3_5_HAIKU,
    
    # Legacy Claude 3.5 models
    AnthropicModels.CLAUDE_3_5_SONNET_LEGACY,
    
    # Claude 3 models
    AnthropicModels.CLAUDE_3_OPUS,
    AnthropicModels.CLAUDE_3_SONNET,
    AnthropicModels.CLAUDE_3_HAIKU,
]
