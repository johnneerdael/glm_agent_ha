# Icon 404 Error Fix for GLM Agent HA

## Problem
Users were experiencing 404 errors for the following icon URLs:
- `brands.home-assistant.io/wled_liveviewproxy/dark_icon.png`
- `brands.home-assistant.io/glm_agent_ha/dark_icon.png`
- `brands.home-assistant.io/wled_liveviewproxy/dark_icon@2x.png`

## Root Cause
These errors occur when Home Assistant's frontend tries to fetch brand icons for custom integrations that don't have proper icon definitions. The brands.home-assistant.io service attempts to serve these icons but returns 404s when the brands aren't registered.

## Solution Implemented

### 1. Created Brand Icon Directories
- `/brands/glm_agent_ha/` - Contains GLM Agent HA brand icons
- `/brands/wled_liveviewproxy/` - Contains WLED Live View Proxy brand icons

### 2. Added Icon Files
- `dark_icon.png` - Standard 24x24 white icon for dark theme
- `dark_icon@2x.png` - High-resolution 48x48 white icon for retina displays

### 3. Icon Configuration
- Updated `manifest.json` to include proper Material Design Icon reference
- Created `brands.yaml` for brand definitions
- Used robot/AI theme icon for GLM Agent HA
- Used LED/lighting theme icon for WLED Live View Proxy

### 4. File Structure
```
brands/
├── brands.yaml
├── glm_agent_ha/
│   ├── dark_icon.png
│   └── dark_icon@2x.png
└── wled_liveviewproxy/
    ├── dark_icon.png
    └── dark_icon@2x.png
```

## Testing
After deployment, the 404 errors should be resolved as:
1. Home Assistant will find the local brand icons
2. The Material Design Icons will be used as fallbacks
3. The frontend will properly display integration icons

## Additional Notes
- Icons are provided as SVG files with white fill for dark theme compatibility
- The robot icon (mdi:robot) represents the AI/automation nature of GLM Agent HA
- The LED strip icon (mdi:led-strip-variant) represents the WLED functionality
- All icons follow Home Assistant's design guidelines