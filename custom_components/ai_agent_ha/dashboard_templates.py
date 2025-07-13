"""
Dashboard templates and examples for AI agent to use when creating dashboards.
"""

# Basic dashboard templates for different use cases
DASHBOARD_TEMPLATES = {
    "simple_lights": {
        "title": "Lights Dashboard",
        "url_path": "lights",
        "icon": "mdi:lightbulb",
        "show_in_sidebar": True,
        "views": [
            {
                "title": "All Lights",
                "cards": [
                    {
                        "type": "entities",
                        "title": "Living Room Lights",
                        "entities": [],  # To be filled with actual light entities
                    },
                    {
                        "type": "light",
                        "entity": "",  # To be filled with main light entity
                    },
                ],
            }
        ],
    },
    "security": {
        "title": "Security Dashboard",
        "url_path": "security",
        "icon": "mdi:security",
        "show_in_sidebar": True,
        "views": [
            {
                "title": "Security Overview",
                "cards": [
                    {
                        "type": "entities",
                        "title": "Sensors",
                        "entities": [],  # To be filled with sensor entities
                    },
                    {
                        "type": "entities",
                        "title": "Cameras",
                        "entities": [],  # To be filled with camera entities
                    },
                    {
                        "type": "alarm-panel",
                        "entity": "",  # To be filled with alarm panel entity
                    },
                ],
            }
        ],
    },
    "climate": {
        "title": "Climate Control",
        "url_path": "climate",
        "icon": "mdi:thermometer",
        "show_in_sidebar": True,
        "views": [
            {
                "title": "Temperature Control",
                "cards": [
                    {
                        "type": "thermostat",
                        "entity": "",  # To be filled with thermostat entity
                    },
                    {
                        "type": "entities",
                        "title": "Temperature Sensors",
                        "entities": [],  # To be filled with temperature sensor entities
                    },
                    {
                        "type": "weather-forecast",
                        "entity": "",  # To be filled with weather entity
                    },
                ],
            }
        ],
    },
    "media": {
        "title": "Media Center",
        "url_path": "media",
        "icon": "mdi:play",
        "show_in_sidebar": True,
        "views": [
            {
                "title": "Media Players",
                "cards": [
                    {
                        "type": "media-control",
                        "entity": "",  # To be filled with media player entity
                    },
                    {
                        "type": "entities",
                        "title": "All Media Players",
                        "entities": [],  # To be filled with media player entities
                    },
                ],
            }
        ],
    },
    "energy": {
        "title": "Energy Monitoring",
        "url_path": "energy",
        "icon": "mdi:lightning-bolt",
        "show_in_sidebar": True,
        "views": [
            {
                "title": "Energy Usage",
                "cards": [
                    {"type": "energy-distribution", "title": "Energy Distribution"},
                    {
                        "type": "entities",
                        "title": "Power Sensors",
                        "entities": [],  # To be filled with power sensor entities
                    },
                    {
                        "type": "history-graph",
                        "title": "Power Usage",
                        "entities": [],  # To be filled with power entities
                    },
                ],
            }
        ],
    },
}

# Card type examples and their typical use cases
CARD_EXAMPLES = {
    "entities": {
        "description": "Shows a list of entities with their states",
        "example": {
            "type": "entities",
            "title": "Living Room",
            "entities": [
                "light.living_room_main",
                "switch.living_room_fan",
                "sensor.living_room_temperature",
            ],
        },
    },
    "glance": {
        "description": "Shows entities in a compact grid format",
        "example": {
            "type": "glance",
            "title": "Quick Overview",
            "entities": [
                "binary_sensor.front_door",
                "binary_sensor.back_door",
                "binary_sensor.garage_door",
            ],
        },
    },
    "thermostat": {
        "description": "Controls and displays thermostat information",
        "example": {"type": "thermostat", "entity": "climate.main_thermostat"},
    },
    "weather-forecast": {
        "description": "Shows weather information and forecast",
        "example": {
            "type": "weather-forecast",
            "entity": "weather.home",
            "name": "Weather",
        },
    },
    "media-control": {
        "description": "Controls media players with full interface",
        "example": {"type": "media-control", "entity": "media_player.living_room_tv"},
    },
    "light": {
        "description": "Dedicated light control card",
        "example": {"type": "light", "entity": "light.living_room_main"},
    },
    "alarm-panel": {
        "description": "Security alarm panel interface",
        "example": {"type": "alarm-panel", "entity": "alarm_control_panel.home_alarm"},
    },
    "picture-entity": {
        "description": "Shows entity state with a background image",
        "example": {
            "type": "picture-entity",
            "entity": "light.living_room",
            "image": "/local/living_room.jpg",
        },
    },
    "history-graph": {
        "description": "Shows historical data as a graph",
        "example": {
            "type": "history-graph",
            "title": "Temperature History",
            "entities": ["sensor.temperature_indoor", "sensor.temperature_outdoor"],
            "hours_to_show": 24,
        },
    },
    "gauge": {
        "description": "Shows a single entity value as a gauge",
        "example": {
            "type": "gauge",
            "entity": "sensor.cpu_temperature",
            "min": 0,
            "max": 100,
            "name": "CPU Temperature",
        },
    },
}

# Predefined color schemes and icons
COMMON_ICONS = {
    "lights": "mdi:lightbulb",
    "security": "mdi:security",
    "climate": "mdi:thermometer",
    "energy": "mdi:lightning-bolt",
    "media": "mdi:play",
    "kitchen": "mdi:chef-hat",
    "bedroom": "mdi:bed",
    "bathroom": "mdi:shower",
    "living_room": "mdi:sofa",
    "garage": "mdi:garage",
    "garden": "mdi:flower",
    "office": "mdi:desk",
    "basement": "mdi:stairs-down",
    "attic": "mdi:stairs-up",
}


def get_template_for_entities(entities, dashboard_type="general"):
    """Generate a dashboard template based on available entities."""
    template = {
        "title": f"{dashboard_type.title()} Dashboard",
        "url_path": dashboard_type.lower().replace(" ", "-"),
        "icon": COMMON_ICONS.get(dashboard_type, "mdi:view-dashboard"),
        "show_in_sidebar": True,
        "views": [],
    }

    # Group entities by domain
    entity_groups = {}
    for entity in entities:
        if isinstance(entity, dict) and "entity_id" in entity:
            entity_id = entity["entity_id"]
        else:
            entity_id = str(entity)

        domain = entity_id.split(".")[0]
        if domain not in entity_groups:
            entity_groups[domain] = []
        entity_groups[domain].append(entity_id)

    # Create view with cards for each domain
    view_cards = []

    # Lights
    if "light" in entity_groups:
        view_cards.append(
            {"type": "entities", "title": "Lights", "entities": entity_groups["light"]}
        )

    # Climate
    if "climate" in entity_groups:
        for climate_entity in entity_groups["climate"]:
            view_cards.append({"type": "thermostat", "entity": climate_entity})

    # Media players
    if "media_player" in entity_groups:
        for media_entity in entity_groups["media_player"]:
            view_cards.append({"type": "media-control", "entity": media_entity})

    # Security entities
    if "binary_sensor" in entity_groups:
        view_cards.append(
            {
                "type": "entities",
                "title": "Sensors",
                "entities": entity_groups["binary_sensor"],
            }
        )

    if "alarm_control_panel" in entity_groups:
        for alarm_entity in entity_groups["alarm_control_panel"]:
            view_cards.append({"type": "alarm-panel", "entity": alarm_entity})

    # Sensors
    if "sensor" in entity_groups:
        view_cards.append(
            {
                "type": "entities",
                "title": "Sensors",
                "entities": entity_groups["sensor"][:10],  # Limit to first 10
            }
        )

    # Switches
    if "switch" in entity_groups:
        view_cards.append(
            {
                "type": "entities",
                "title": "Switches",
                "entities": entity_groups["switch"],
            }
        )

    # Weather
    if "weather" in entity_groups:
        view_cards.append(
            {"type": "weather-forecast", "entity": entity_groups["weather"][0]}
        )

    template["views"] = [{"title": "Overview", "cards": view_cards}]

    return template
