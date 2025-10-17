# HTTP Registration Error in GLM Coding Plan Agent HA Integration

## Issue Type
- **Bug Report**
- **Component**: Custom Integration (GLM Coding Plan Agent HA)
- **Severity**: High - Prevents integration from loading

## Environment Details

**Home Assistant Version**:
- All recent versions (2024.x)
- Error occurs in production environment

**Integration Version**:
- GLM Coding Plan Agent HA v1.10.6
- Domain: `glm_agent_ha`

**Installation Method**:
- HACS (Home Assistant Community Store)
- Custom component installation

## Error Description

The GLM Coding Plan Agent HA integration fails to load due to an HTTP static path registration error. The issue occurs during the `async_setup_entry` phase when the integration attempts to register static HTTP routes for the frontend panel.

## Complete Error Traceback

```
Error setting up entry GLM Coding Plan Agent HA (GLM Coding Pro - GLM-4.6) for glm_agent_ha
Traceback (most recent call last):
  File "/usr/src/homeassistant/homeassistant/config_entries.py", line 761, in __async_setup_with_context
    result = await component.async_setup_entry(hass, self)
  File "/config/custom_components/glm_agent_ha/__init__.py", line 1052, in async_setup_entry
    await hass.http.async_register_static_paths([
  File "/usr/src/homeassistant/homeassistant/components/http/__init__.py", line 478, in async_register_static_paths
    self._async_register_static_paths(configs, resources)
  File "/usr/src/homeassistant/homeassistant/components/http/__init__.py", line 498, in _async_register_static_paths
    self.app.router.add_static(...)
AttributeError: 'NoneType' object has no attribute 'add_static'
```

## Root Cause Analysis

### 1. **Timing Issue with HTTP Component Initialization**

The error occurs because the integration attempts to register HTTP static paths before Home Assistant's HTTP component is fully initialized. The `hass.http.app.router` is `None` at the time of registration.

### 2. **Outdated SimpleNamespace Pattern vs StaticPathConfig**

The integration uses an outdated pattern of creating `SimpleNamespace` objects for static path configuration, while newer Home Assistant versions expect `StaticPathConfig` objects:

```python
# Current (problematic) approach:
route_info = SimpleNamespace(
    url_path=url_path,
    path=file_path,
    cache_headers=cache_headers,
    registered_at=time.time()
)
await hass.http.async_register_static_paths([route_info])

# Required approach for newer HA versions:
from homeassistant.components.http import StaticPathConfig
route_config = StaticPathConfig(
    url_path=url_path,
    path=file_path,
    cache_headers=cache_headers
)
await hass.http.async_register_static_paths([route_config])
```

### 3. **Missing HTTP Component Availability Check**

The integration doesn't verify that the HTTP component is ready before attempting registration:

```python
# Missing validation:
if hass.http is None or hass.http.app is None:
    _LOGGER.warning("HTTP component not ready, deferring static path registration")
    return False
```

## Step-by-Step Reproduction

1. **Install GLM Coding Plan Agent HA** via HACS or manual installation
2. **Configure the integration** with valid AI provider credentials
3. **Restart Home Assistant** or reload the integration
4. **Observe the error** in Home Assistant logs
5. **Integration fails to load** and dashboard features are unavailable

## Expected vs Actual Behavior

### Expected Behavior:
- Integration loads successfully
- Frontend panel is accessible via `/frontend/glm_agent_ha/glm_agent_ha-panel.js`
- Dashboard features work properly
- No HTTP registration errors

### Actual Behavior:
- Integration fails to load during setup
- HTTP static path registration throws AttributeError
- Frontend panel is unavailable
- Error traceback appears in logs

## Technical Analysis

### HTTP Component Initialization Timing Issue

The error indicates a race condition where:
1. Integration's `async_setup_entry` is called
2. Integration attempts to register HTTP static paths immediately
3. Home Assistant's HTTP component router is not yet initialized (`router` is `None`)
4. `router.add_static()` call fails with AttributeError

### Home Assistant HTTP Architecture Changes

Recent Home Assistant versions have updated the HTTP static path registration system:
- **Old pattern**: `SimpleNamespace` objects with arbitrary attributes
- **New pattern**: `StaticPathConfig` objects with validated structure
- **Required attributes**: `url_path`, `path`, `cache_headers`

## Proposed Solution

### 1. **Immediate Fix - HTTP Component Check**

Add proper HTTP component validation before registration:

```python
async def async_register_static_route_with_validation(
    hass: HomeAssistant,
    url_path: str,
    file_path: str,
    cache_headers: bool = False
) -> bool:
    """Register a static route with validation and deduplication."""
    try:
        # Validate HTTP component is ready
        if hass.http is None:
            _LOGGER.error("HTTP component not available for static route registration")
            return False

        if hass.http.app is None:
            _LOGGER.error("HTTP app not initialized for static route registration")
            return False

        if hass.http.app.router is None:
            _LOGGER.error("HTTP router not available for static route registration")
            return False

        # Validate file path exists
        import os
        if not os.path.exists(file_path):
            _LOGGER.error("Static file does not exist: %s", file_path)
            return False

        # Use StaticPathConfig for newer HA versions
        try:
            from homeassistant.components.http import StaticPathConfig
            route_config = StaticPathConfig(
                url_path=url_path,
                path=file_path,
                cache_headers=cache_headers
            )
        except ImportError:
            # Fallback to SimpleNamespace for older HA versions
            route_config = SimpleNamespace(
                url_path=url_path,
                path=file_path,
                cache_headers=cache_headers,
                registered_at=time.time()
            )

        # Check for existing registration
        registry = get_route_registry()
        if registry.is_route_registered(url_path):
            _LOGGER.warning("Static route %s already registered, reusing existing route", url_path)
            return True

        # Register in our registry first
        if not registry.register_route(url_path, route_config):
            return False

        # Register with Home Assistant
        try:
            await hass.http.async_register_static_paths([route_config])
            _LOGGER.info("Successfully registered static route: %s -> %s", url_path, file_path)
            return True
        except Exception as e:
            # Rollback registration in our registry if HA registration failed
            registry.unregister_route(url_path)
            _LOGGER.error("Failed to register static route %s with Home Assistant: %s", url_path, e)
            return False

    except Exception as e:
        _LOGGER.error("Error registering static route %s: %s", url_path, e)
        return False
```

### 2. **Future-Proofing - Version-Aware Registration**

Implement version-aware HTTP registration:

```python
async def async_register_static_routes_compatible(
    hass: HomeAssistant,
    routes: List[Union[StaticPathConfig, SimpleNamespace]]
) -> bool:
    """Register static routes with Home Assistant version compatibility."""
    try:
        # Check HTTP component availability
        if not (hasattr(hass, 'http') and hass.http and
                hasattr(hass.http, 'app') and hass.http.app and
                hasattr(hass.http.app, 'router') and hass.http.app.router):
            _LOGGER.warning("HTTP component not ready, deferring route registration")
            return False

        # Use newer StaticPathConfig if available
        try:
            from homeassistant.components.http import StaticPathConfig
            # Convert to StaticPathConfig if needed
            compatible_routes = []
            for route in routes:
                if isinstance(route, StaticPathConfig):
                    compatible_routes.append(route)
                elif hasattr(route, 'url_path') and hasattr(route, 'path'):
                    compatible_routes.append(StaticPathConfig(
                        url_path=route.url_path,
                        path=route.path,
                        cache_headers=getattr(route, 'cache_headers', False)
                    ))
                else:
                    _LOGGER.error("Invalid route configuration: %s", route)
                    return False

            await hass.http.async_register_static_paths(compatible_routes)
            return True

        except ImportError:
            # Fallback for older HA versions
            await hass.http.async_register_static_paths(routes)
            return True

    except Exception as e:
        _LOGGER.error("Failed to register static routes: %s", e)
        return False
```

### 3. **Deferred Registration Strategy**

Implement deferred registration if HTTP component is not ready:

```python
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up GLM Coding Plan Agent HA from a config entry."""
    # ... existing setup code ...

    # Defer HTTP registration if needed
    static_route_registered = False
    max_retries = 3
    retry_delay = 1  # seconds

    for attempt in range(max_retries):
        static_route_registered = await async_register_static_route_with_validation(
            hass,
            "/frontend/glm_agent_ha/glm_agent_ha-panel.js",
            hass.config.path("custom_components/glm_agent_ha/frontend/glm_agent_ha-panel.js"),
            cache_headers=False,
        )

        if static_route_registered:
            break

        if attempt < max_retries - 1:
            _LOGGER.warning("HTTP registration attempt %d failed, retrying in %d seconds",
                          attempt + 1, retry_delay)
            await asyncio.sleep(retry_delay)
            retry_delay *= 2  # Exponential backoff

    if not static_route_registered:
        _LOGGER.warning("Failed to register static route for frontend panel after %d attempts - dashboard features may be unavailable", max_retries)

    # Continue with rest of setup...
    return True
```

## Implementation Suggestions

### For Integration Maintainers:

1. **Update the HTTP registration code** in `/custom_components/glm_agent_ha/__init__.py`
2. **Add proper error handling** for HTTP component availability
3. **Implement version compatibility** for different Home Assistant versions
4. **Add logging** to help diagnose timing issues
5. **Test thoroughly** across different Home Assistant versions

### For Home Assistant Core Team:

1. **Consider improving HTTP component initialization ordering** to prevent race conditions
2. **Add better error messages** when HTTP router is not available
3. **Document the StaticPathConfig migration** for custom integration developers

### For Users Experiencing This Issue:

**Temporary Workaround:**
1. Restart Home Assistant
2. Check if integration loads on second attempt
3. Monitor logs for successful registration

**Permanent Fix:**
1. Wait for integration update
2. Update to latest version when available
3. Report if issue persists

## Impact Assessment

- **User Impact**: High - Integration completely unusable
- **System Impact**: Low - Only affects this specific integration
- **Frequency**: Occurs on every integration load/reload
- **Workarounds**: Limited - Restart sometimes helps

## Related Issues

- This is a common pattern issue affecting multiple custom integrations
- Home Assistant core changes in HTTP registration affect compatibility
- Need for better documentation on HTTP component usage

## Files to Modify

1. `/custom_components/glm_agent_ha/__init__.py`
   - Lines 148-196: `async_register_static_route_with_validation` function
   - Lines 172-177: Static route registration call
   - Add proper HTTP component validation

2. `/custom_components/glm_agent_ha/const.py`
   - Consider adding HTTP-related constants for retry configuration

## Testing Recommendations

1. **Test across Home Assistant versions** (2024.1 through latest)
2. **Test timing scenarios** (fresh install, restart, reload)
3. **Test with and without HTTP component** availability
4. **Test frontend panel functionality** after successful registration
5. **Test error handling** with invalid file paths

## Security Considerations

- Ensure file path validation prevents directory traversal
- Validate that registered paths are within the integration's directory
- Consider rate limiting for registration attempts
- Log registration attempts for audit purposes

## Conclusion

This HTTP registration error prevents the GLM Coding Plan Agent HA integration from loading properly. The issue stems from timing problems with Home Assistant's HTTP component initialization and outdated registration patterns. The proposed solution provides both immediate fixes and future-proofing to ensure compatibility across Home Assistant versions.

Implementing the suggested changes will resolve the loading failure and restore full functionality to the integration's dashboard features.