# AI Agent Dashboard Creation

This document explains how to use the AI Agent to create and manage Home Assistant dashboards.

## Overview

The AI Agent HA integration now supports creating and managing Home Assistant dashboards through natural language conversations. The AI can:

- Create new dashboards based on your requirements
- Update existing dashboards
- Query available entities and organize them into logical dashboard layouts
- Ask follow-up questions to clarify your dashboard requirements
- Suggest appropriate card types and layouts

## How It Works

The AI Agent uses the following workflow for dashboard creation:

1. **Requirement Gathering**: When you ask to create a dashboard, the AI will gather information about your needs
2. **Entity Analysis**: The AI queries your Home Assistant instance to understand available entities
3. **Dashboard Design**: Based on your requirements and available entities, the AI creates a dashboard configuration
4. **Implementation**: The AI creates the dashboard files and updates your Home Assistant configuration
5. **Follow-up**: The AI can make adjustments or answer questions about the created dashboard

## Usage Examples

### Creating a Simple Dashboard

```
"Create a dashboard for my living room lights"
```

The AI will:
- Query your light entities
- Filter for living room lights
- Create a dashboard with appropriate light control cards
- Set up the dashboard with a logical layout

### Creating a Comprehensive Dashboard

```
"Create a security dashboard that shows all my door sensors, cameras, and alarm controls"
```

The AI will:
- Query for security-related entities (binary sensors, cameras, alarm panels)
- Ask clarifying questions if needed
- Create a multi-view dashboard with:
  - Sensor overview
  - Camera feeds
  - Alarm control panel
  - Recent security events

### Creating a Room-Specific Dashboard

```
"I want a kitchen dashboard with lights, temperature sensor, and appliance controls"
```

The AI will:
- Find entities related to the kitchen area
- Create appropriate cards for each entity type
- Organize them in a logical layout
- Include relevant controls and status displays

## Dashboard Features

### Supported Card Types

The AI can create dashboards using these Home Assistant card types:

- **Entities Card**: List of entities with states and controls
- **Glance Card**: Compact grid view of entity states
- **Thermostat Card**: Climate control interface
- **Weather Forecast Card**: Weather information display
- **Media Control Card**: Media player controls
- **Light Card**: Dedicated light controls
- **Alarm Panel Card**: Security system interface
- **Picture Entity Card**: Entity with background image
- **History Graph Card**: Historical data visualization
- **Gauge Card**: Single value displays

### Dashboard Organization

Dashboards are automatically organized by:

- **Entity Domain**: Lights, sensors, switches grouped logically
- **Room/Area**: Entities grouped by location when detected
- **Functionality**: Related controls grouped together
- **Priority**: Most important controls placed prominently

## AI Interaction Flow

### Initial Request
```
User: "Create a dashboard for energy monitoring"
```

### AI Information Gathering
```
AI: "I'll create an energy monitoring dashboard for you. Let me first check what energy-related entities you have available."

[AI queries power sensors, energy meters, solar panels, etc.]

AI: "I found several energy entities. Would you like to include:
- Real-time power consumption
- Daily energy usage graphs
- Solar production (if applicable)
- Individual device monitoring
- Cost tracking

What would you like to focus on?"
```

### User Clarification
```
User: "I want to see real-time power usage and daily graphs for the main house consumption"
```

### AI Dashboard Creation
```
AI: "Perfect! I'll create an energy dashboard with:
- Current power consumption gauge
- Daily energy usage graph
- Monthly cost tracking
- Top energy consumers

Creating the dashboard now..."

[AI creates the dashboard]

AI: "Energy dashboard created successfully! You can find it in your sidebar as 'Energy Monitoring'. The dashboard includes real-time power monitoring and historical usage graphs. Would you like me to add any other energy-related information?"
```

## Advanced Features

### Follow-up Questions

The AI will ask clarifying questions when:
- Multiple entities match your criteria
- Your request is ambiguous
- Better organization options are available
- Additional relevant entities are found

Example:
```
User: "Create a lights dashboard"
AI: "I found lights in multiple rooms. Would you like:
1. All lights in one dashboard
2. Separate views for each room
3. Group by light type (overhead, lamps, accent)
4. Focus on specific rooms

Also, I noticed you have some smart switches controlling lights - should I include those as well?"
```

### Template-Based Creation

The AI uses intelligent templates for common dashboard types:
- Security monitoring
- Climate control
- Media centers
- Energy monitoring
- Room-specific controls

### Dynamic Entity Discovery

The AI automatically:
- Discovers related entities
- Suggests relevant additions
- Organizes by areas/rooms when possible
- Filters out irrelevant entities

## Technical Details

### Dashboard Configuration

Created dashboards include:
- **Title and URL**: Descriptive names and clean URLs
- **Icons**: Appropriate Material Design icons
- **Sidebar Integration**: Automatic sidebar placement
- **View Organization**: Logical view structure
- **Card Layout**: Optimized card arrangements

### File Management

The AI creates:
- Dashboard YAML files in `/config/dashboards/`
- Updates to `configuration.yaml` if needed
- Proper dashboard registration

### Error Handling

The system handles:
- Missing entities gracefully
- Invalid configurations
- Permission issues
- File system errors

## Service Calls

### Available Services

The integration provides these services:

#### `ai_agent_ha.query`
Natural language dashboard requests through the main query interface.

```yaml
service: ai_agent_ha.query
data:
  prompt: "Create a living room dashboard"
  provider: "openai"  # optional
```

#### `ai_agent_ha.create_dashboard`
Direct dashboard creation (for advanced users).

```yaml
service: ai_agent_ha.create_dashboard
data:
  dashboard_config:
    title: "My Dashboard"
    url_path: "my-dashboard"
    views:
      - title: "Overview"
        cards:
          - type: "entities"
            entities: ["light.living_room"]
```

#### `ai_agent_ha.update_dashboard`
Update existing dashboards.

```yaml
service: ai_agent_ha.update_dashboard
data:
  dashboard_url: "my-dashboard"
  dashboard_config:
    title: "Updated Dashboard"
    views: [...]
```

## Best Practices

### Clear Requirements
Be specific about what you want:
- "Kitchen lights and appliances" vs "Kitchen stuff"
- "Security cameras and door sensors" vs "Security things"

### Room Organization
Mention specific rooms or areas:
- "Living room entertainment center"
- "Bedroom climate control"
- "Garage workshop controls"

### Functionality Focus
Specify the main purpose:
- "Morning routine dashboard"
- "Evening security check"
- "Energy optimization center"

## Troubleshooting

### Common Issues

1. **Dashboard Not Appearing**
   - Check if Home Assistant restart is required
   - Verify dashboard was created in configuration
   - Check for configuration errors in logs

2. **Missing Entities**
   - Ensure entities exist and are enabled
   - Check entity naming and availability
   - Verify permissions and access rights

3. **Layout Issues**
   - Ask AI to reorganize the dashboard
   - Request specific card types
   - Modify through standard HA dashboard editor

### Getting Help

If you encounter issues:
1. Check the Home Assistant logs for errors
2. Ask the AI to troubleshoot: "Check my energy dashboard creation"
3. Use the AI to modify or recreate dashboards
4. Report issues with specific error messages

## Future Enhancements

Planned improvements include:
- Custom card support
- Theme integration
- Advanced layout options
- Dashboard templates
- Multi-user customization
- Mobile-optimized layouts

---

The AI Agent Dashboard Creation feature makes it easy to create beautiful, functional Home Assistant dashboards through natural conversation. Simply describe what you want, and the AI will handle the technical details! 