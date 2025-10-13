"""Tests for the ContextCacheManager."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from homeassistant.core import HomeAssistant, Event
from homeassistant.const import EVENT_HOMEASSISTANT_STOP

from custom_components.glm_agent_ha.context.cache import ContextCacheManager

@pytest.fixture
def mock_hass():
    """Fixture for a mock HomeAssistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.bus = MagicMock()
    return hass

@pytest.fixture
def cache_manager(mock_hass):
    """Fixture for a ContextCacheManager instance."""
    return ContextCacheManager(hass=mock_hass)

def test_initialization(cache_manager: ContextCacheManager, mock_hass: HomeAssistant):
    """Test that the cache manager initializes correctly."""
    assert cache_manager.hass is mock_hass
    assert cache_manager._cache == {}
    # The new implementation does not use _cache_timestamps
    # The event listener is now for registry updates, not stop events
    assert mock_hass.bus.async_listen.call_count >= 3

@pytest.mark.asyncio
async def test_get_set_cache(cache_manager: ContextCacheManager):
    """Test setting and getting cache data."""
    cache_manager._store("test_key", {"data": "value"})
    cached_data = await cache_manager.get_or_refresh("test_key", loader=lambda: None)
    
    assert cached_data is not None
    assert cached_data["data"] == "value"
    assert "test_key" in cache_manager._cache

@pytest.mark.asyncio
async def test_is_cache_valid(cache_manager: ContextCacheManager):
    """Test the cache validity logic."""
    cache_manager._store("test_key", {"data": "value"})
    
    # Test with default TTL (should be valid)
    entry = cache_manager._cache.get("test_key")
    assert entry is not None
    assert not entry.is_expired()
    
    # Test with expired TTL
    entry.ttl = -1
    assert entry.is_expired() is True

@pytest.mark.asyncio
async def test_clear_cache(cache_manager: ContextCacheManager):
    """Test clearing a specific cache."""
    cache_manager._store("test_key", {"data": "value"})
    cache_manager.invalidate("test_key")
    
    cached_data = cache_manager._cache.get("test_key")
    assert cached_data is None

def test_invalidate_all_caches(cache_manager: ContextCacheManager):
    """Test the invalidate method for all caches."""
    cache_manager._store("test_key", {"data": "value"})
    
    cache_manager.invalidate()
    
    assert cache_manager._cache == {}

@patch("homeassistant.helpers.area_registry.async_get")
@pytest.mark.asyncio
async def test_get_area_registry(mock_async_get, cache_manager: ContextCacheManager, mock_hass: HomeAssistant):
    """Test fetching and caching the area registry."""
    mock_area = MagicMock()
    mock_area.id = "living_room"
    mock_area.name = "Living Room"
    mock_area.normalized_name = "living_room"

    mock_registry = MagicMock()
    mock_registry.areas = {"living_room": mock_area}
    mock_async_get.return_value = mock_registry
    
    areas = await cache_manager.get_area_registry()
    
    assert "living_room" in areas
    assert areas["living_room"]["name"] == "Living Room"
    
    # Verify it was cached
    cached_areas = cache_manager._cache.get("area_registry")
    assert cached_areas is not None
