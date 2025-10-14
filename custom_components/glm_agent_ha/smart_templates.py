"""Smart action templates for GLM Agent HA integration."""

from __future__ import annotations

from typing import Dict, List, Any

SMART_ACTION_TEMPLATES = {
    "automation": {
        "name": "Automation Templates",
        "description": "Pre-built automation templates for common Home Assistant scenarios",
        "icon": "mdi:robot",
        "templates": [
            {
                "id": "smart_lighting_automation",
                "name": "Smart Lighting Automation",
                "description": "Create intelligent lighting automations based on motion, time, and ambient light",
                "prompt": """Create a comprehensive smart lighting automation system for my home with the following features:

1. Motion-activated lights in hallways and bathrooms during nighttime
2. Ambient light sensing to only turn on lights when needed
3. Gradual dimming in the evening to prepare for sleep
4. Vacation mode to simulate occupancy when away
5. Energy-saving settings to optimize usage

Please generate:
- Complete automation YAML files
- Helper entities needed
- Configuration instructions
- Energy usage optimization tips""",
                "category": "lighting",
                "complexity": "intermediate",
                "estimated_time": "15-30 minutes",
                "required_entities": ["motion sensors", "light entities", "ambient light sensors"],
                "tags": ["lighting", "motion", "energy", "security"]
            },
            {
                "id": "climate_control_automation",
                "name": "Climate Control System",
                "description": "Intelligent HVAC automation with comfort optimization and energy efficiency",
                "prompt": """Design an advanced climate control automation system that:

1. Learns household preferences and schedules
2. Optimizes temperature based on occupancy and time
3. Integrates weather forecasts for pre-heating/cooling
4. Provides energy usage insights and savings
5. Includes away mode and vacation settings

Generate:
- Complete thermostat automations
- Weather integration setup
- Energy monitoring dashboard
- Comfort optimization algorithms
- Seasonal adjustment configurations""",
                "category": "climate",
                "complexity": "advanced",
                "estimated_time": "30-45 minutes",
                "required_entities": ["thermostats", "temperature sensors", "weather integration"],
                "tags": ["climate", "energy", "comfort", "weather"]
            },
            {
                "id": "security_monitoring_automation",
                "name": "Security Monitoring System",
                "description": "Comprehensive home security with smart alerts and automated responses",
                "prompt": """Create a robust home security automation system featuring:

1. Perimeter monitoring with door/window sensors
2. Motion detection with pet immunity
3. Camera integration with smart alerts
4. Automated lighting responses to security events
5. Emergency notification system

Please provide:
- Security automations for different modes (home/away/night)
- Camera integration and alert logic
- Notification systems and escalation
- Integration with existing security systems
- Privacy-focused configuration options""",
                "category": "security",
                "complexity": "advanced",
                "estimated_time": "45-60 minutes",
                "required_entities": ["door/window sensors", "cameras", "motion sensors"],
                "tags": ["security", "monitoring", "alerts", "cameras"]
            }
        ]
    },
    "dashboard": {
        "name": "Dashboard Templates",
        "description": "Pre-designed dashboard layouts for different use cases",
        "icon": "mdi:view-dashboard",
        "templates": [
            {
                "id": "home_overview_dashboard",
                "name": "Home Overview Dashboard",
                "description": "Complete home status dashboard with all essential information",
                "prompt": """Create a comprehensive home overview dashboard that displays:

1. Current weather and forecast
2. Indoor climate conditions (temperature, humidity, air quality)
3. Security status (doors, windows, cameras)
4. Energy consumption monitoring
5. Active automations and device status
6. Calendar and reminders
7. Quick action buttons for common controls

Generate:
- Complete Lovelace dashboard YAML
- Card configurations and layouts
- Sensor requirements and setup
- Color schemes and styling
- Mobile-responsive design considerations""",
                "category": "overview",
                "complexity": "intermediate",
                "estimated_time": "20-30 minutes",
                "required_entities": ["weather", "climate sensors", "security sensors", "energy monitoring"],
                "tags": ["dashboard", "overview", "monitoring", "essential"]
            },
            {
                "id": "energy_monitoring_dashboard",
                "name": "Energy Monitoring Dashboard",
                "description": "Detailed energy consumption and cost analysis dashboard",
                "prompt": """Design an advanced energy monitoring dashboard that provides:

1. Real-time power consumption tracking
2. Historical energy usage charts and trends
3. Cost analysis and budget tracking
4. Device-level consumption breakdown
5. Solar generation monitoring (if applicable)
6. Energy-saving recommendations
7. Carbon footprint tracking

Generate:
- Complete dashboard configuration
- Energy sensor setup and calibration
- Cost calculation automations
- Historical data storage and retrieval
- Alert configurations for unusual consumption patterns""",
                "category": "energy",
                "complexity": "advanced",
                "estimated_time": "30-45 minutes",
                "required_entities": ["energy monitors", "smart plugs", "solar sensors"],
                "tags": ["energy", "monitoring", "costs", "sustainability"]
            },
            {
                "id": "entertainment_dashboard",
                "name": "Entertainment Control Dashboard",
                "description": "Unified media and entertainment system control center",
                "prompt": """Create an entertainment control dashboard featuring:

1. Media player controls for all devices
2. Scene-based lighting for movie/music modes
3. Volume and playback synchronization
4. Content recommendations and discovery
5. Voice control integration
6. Room-to-room audio distribution

Generate:
- Complete entertainment dashboard layout
- Media player integration configurations
- Scene automation templates
- Voice command setup instructions
- Multi-room audio synchronization""",
                "category": "entertainment",
                "complexity": "intermediate",
                "estimated_time": "25-35 minutes",
                "required_entities": ["media players", "smart lights", "speakers"],
                "tags": ["entertainment", "media", "lighting", "scenes"]
            }
        ]
    },
    "analysis": {
        "name": "Analysis Templates",
        "description": "Templates for analyzing and optimizing Home Assistant data",
        "icon": "mdi:chart-line",
        "templates": [
            {
                "id": "device_usage_analysis",
                "name": "Device Usage Analysis",
                "description": "Analyze how and when devices are used to optimize automation",
                "prompt": """Create a comprehensive device usage analysis system that:

1. Tracks device usage patterns and frequency
2. Identifies peak usage times and energy consumption
3. Suggests automation improvements
4. Detects unusual usage patterns
5. Provides maintenance recommendations

Generate:
- Database queries and sensors for usage tracking
- Analysis automations and calculations
- Dashboard cards for usage visualization
- Alert configurations for unusual patterns
- Optimization recommendations engine""",
                "category": "usage",
                "complexity": "advanced",
                "estimated_time": "40-50 minutes",
                "required_entities": ["device state sensors", "energy monitors", "database"],
                "tags": ["analysis", "usage", "optimization", "patterns"]
            },
            {
                "id": "automation_efficiency_analysis",
                "name": "Automation Efficiency Analysis",
                "description": "Measure and improve the effectiveness of your automations",
                "prompt": """Design an automation efficiency analysis system to:

1. Track automation execution frequency and success rates
2. Measure energy and cost savings from automations
3. Identify redundant or conflicting automations
4. Suggest consolidation opportunities
5. Provide ROI calculations for automation investments

Generate:
- Automation logging and tracking system
- Efficiency calculation formulas
- Performance dashboards and reports
- Optimization recommendation engine
- Cost-benefit analysis tools""",
                "category": "efficiency",
                "complexity": "advanced",
                "estimated_time": "35-45 minutes",
                "required_entities": ["automation logs", "energy sensors", "cost data"],
                "tags": ["analysis", "efficiency", "optimization", "automations"]
            }
        ]
    },
    "quick_actions": {
        "name": "Quick Actions",
        "description": "Simple templates for common tasks and improvements",
        "icon": "mdi:lightning-bolt",
        "templates": [
            {
                "id": "goodnight_routine",
                "name": "Goodnight Routine",
                "description": "Create a comprehensive goodnight automation sequence",
                "prompt": """Create a goodnight routine automation that:

1. Gradually dims lights throughout the house
2. Sets thermostat to sleep temperature
3. Arms security system in night mode
4. Locks all doors and closes garage
5. Turns off non-essential devices
6. Sets morning alarm and prepares coffee maker
7. Activates do-not-disturb mode

Generate the complete automation with proper delays and conditions.""",
                "category": "routine",
                "complexity": "beginner",
                "estimated_time": "10-15 minutes",
                "required_entities": ["lights", "thermostat", "security system", "smart locks"],
                "tags": ["routine", "night", "security", "comfort"]
            },
            {
                "id": "morning_startup",
                "name": "Morning Startup Routine",
                "description": "Automated morning routine to start the day right",
                "prompt": """Create a morning startup automation that:

1. Gradually increases bedroom lighting
2. Starts coffee maker or tea kettle
3. Turns on news or music at low volume
4. Adjusts thermostat to comfortable temperature
5. Opens smart blinds (if available)
6. Displays weather and calendar on smart display
7. Deactivates night security mode

Generate complete automation with weekday/weekend variations.""",
                "category": "routine",
                "complexity": "beginner",
                "estimated_time": "10-15 minutes",
                "required_entities": ["lights", "coffee maker", "media player", "thermostat"],
                "tags": ["routine", "morning", "comfort", "automation"]
            },
            {
                "id": "away_mode_setup",
                "name": "Away Mode Setup",
                "description": "Configure away mode for energy savings and security",
                "prompt": """Create an away mode automation that:

1. Turns off all lights and entertainment devices
2. Sets thermostat to energy-saving temperature
3. Arms security system completely
4. Locks all doors and windows
5. Activates camera recording and alerts
6. Starts random light simulation for security
7. Pauses non-essential automations

Generate complete away mode with presence detection integration.""",
                "category": "security",
                "complexity": "intermediate",
                "estimated_time": "15-20 minutes",
                "required_entities": ["presence detection", "security system", "lights", "thermostat"],
                "tags": ["away", "security", "energy", "presence"]
            }
        ]
    }
}

def get_all_templates() -> Dict[str, Any]:
    """Get all smart action templates."""
    return SMART_ACTION_TEMPLATES

def get_template_by_id(template_id: str) -> Dict[str, Any]:
    """Get a specific template by ID."""
    for category in SMART_ACTION_TEMPLATES.values():
        for template in category.get("templates", []):
            if template.get("id") == template_id:
                return template
    return {}

def get_templates_by_category(category: str) -> List[Dict[str, Any]]:
    """Get templates by category."""
    if category in SMART_ACTION_TEMPLATES:
        return SMART_ACTION_TEMPLATES[category].get("templates", [])
    return []

def get_templates_by_complexity(complexity: str) -> List[Dict[str, Any]]:
    """Get templates by complexity level."""
    templates = []
    for category in SMART_ACTION_TEMPLATES.values():
        for template in category.get("templates", []):
            if template.get("complexity") == complexity:
                templates.append(template)
    return templates

def search_templates(query: str) -> List[Dict[str, Any]]:
    """Search templates by query string."""
    query = query.lower()
    matching_templates = []

    for category in SMART_ACTION_TEMPLATES.values():
        for template in category.get("templates", []):
            if (query in template.get("name", "").lower() or
                query in template.get("description", "").lower() or
                any(query in tag.lower() for tag in template.get("tags", []))):
                matching_templates.append(template)

    return matching_templates