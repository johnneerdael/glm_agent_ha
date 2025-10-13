"""Context cache manager for GLM Agent HA integration."""

import asyncio
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from ..const import DEFAULT_CACHE_TTL, DEFAULT_CACHE_MAX_SIZE

_LOGGER = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Represents a cached data entry with TTL."""
    
    data: Any
    timestamp: float
    ttl: float
    
    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        return time.time() > (self.timestamp + self.ttl)


class ContextCacheManager:
    """Manages cached snapshots of Home Assistant registries with TTL and invalidation."""
    
    def __init__(
        self,
        hass: HomeAssistant,
        ttl: float = DEFAULT_CACHE_TTL,
        max_size: int = DEFAULT_CACHE_MAX_SIZE,
    ):
        """Initialize the cache manager."""
        self.hass = hass
        self.ttl = ttl
        self.max_size = max_size
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._loaders: Dict[str, Callable[[], Any]] = {}
        self._setup_listeners()
    
    def _setup_listeners(self) -> None:
        """Set up event listeners for registry updates."""
        # Listen for registry update events to invalidate cache
        self.hass.bus.async_listen("area_registry_updated", self._on_registry_updated)
        self.hass.bus.async_listen("entity_registry_updated", self._on_registry_updated)
        self.hass.bus.async_listen("device_registry_updated", self._on_registry_updated)
    
    async def _on_registry_updated(self, event: Dict[str, Any]) -> None:
        """Handle registry update events by invalidating relevant cache entries."""
        event_type = event.data.get("event_type", "")
        _LOGGER.debug("Registry update event received: %s", event_type)
        
        # Invalidate relevant cache entries based on event type
        if "area" in event_type:
            self.invalidate("area_registry")
        elif "entity" in event_type:
            self.invalidate("entity_registry")
        elif "device" in event_type:
            self.invalidate("device_registry")
        
        # Also invalidate derived data that depends on registries
        self.invalidate("area_topology")
        self.invalidate("entity_capabilities")
    
    def register_loader(self, key: str, loader: Callable[[], Any]) -> None:
        """Register a data loader for a cache key."""
        self._loaders[key] = loader
    
    async def get_or_refresh(self, key: str, loader: Optional[Callable[[], Any]] = None) -> Any:
        """Get data from cache or refresh using the provided loader."""
        # Check cache first
        cache_entry = self._cache.get(key)
        if cache_entry and not cache_entry.is_expired():
            # Move to end (LRU)
            self._cache.move_to_end(key)
            _LOGGER.debug("Cache hit for key: %s", key)
            return cache_entry.data
        
        # Use provided loader or registered loader
        if loader is None:
            loader = self._loaders.get(key)
        
        if loader is None:
            raise ValueError(f"No loader registered for cache key: {key}")
        
        # Load fresh data
        _LOGGER.debug("Cache miss for key: %s, loading fresh data", key)
        try:
            if asyncio.iscoroutinefunction(loader):
                data = await loader()
            else:
                data = loader()
            
            # Store in cache
            self._store(key, data)
            return data
        except Exception as e:
            _LOGGER.error("Failed to load data for key %s: %s", key, e)
            raise
    
    def _store(self, key: str, data: Any) -> None:
        """Store data in cache with TTL."""
        # Remove oldest entries if cache is full
        while len(self._cache) >= self.max_size:
            oldest_key = next(iter(self._cache))
            self._cache.pop(oldest_key)
            _LOGGER.debug("Evicted oldest cache entry: %s", oldest_key)
        
        # Store new entry
        entry = CacheEntry(data=data, timestamp=time.time(), ttl=self.ttl)
        self._cache[key] = entry
        _LOGGER.debug("Stored data in cache for key: %s", key)
    
    def invalidate(self, key: Optional[str] = None) -> None:
        """Invalidate cache entries."""
        if key is None:
            # Invalidate all entries
            self._cache.clear()
            _LOGGER.debug("Invalidated all cache entries")
        else:
            # Invalidate specific entry
            if key in self._cache:
                del self._cache[key]
                _LOGGER.debug("Invalidated cache entry: %s", key)
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about cache state."""
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "ttl": self.ttl,
            "keys": list(self._cache.keys()),
            "expired_keys": [
                key for key, entry in self._cache.items() if entry.is_expired()
            ],
        }
    
    # Registry-specific convenience methods
    async def get_area_registry(self) -> Dict[str, Dict[str, Any]]:
        """Get cached area registry data."""
        return await self.get_or_refresh(
            "area_registry",
            self._load_area_registry,
        )
    
    async def get_entity_registry(self) -> List[Dict[str, Any]]:
        """Get cached entity registry data."""
        return await self.get_or_refresh(
            "entity_registry",
            self._load_entity_registry,
        )
    
    async def get_device_registry(self) -> List[Dict[str, Any]]:
        """Get cached device registry data."""
        return await self.get_or_refresh(
            "device_registry",
            self._load_device_registry,
        )
    
    async def _load_area_registry(self) -> Dict[str, Dict[str, Any]]:
        """Load area registry data."""
        registry = ar.async_get(self.hass)
        return {
            area.id: {
                "area_id": area.id,
                "name": area.name,
                "normalized_name": area.normalized_name,
                "picture": area.picture,
                "icon": area.icon,
                "floor_id": area.floor_id,
                "labels": list(area.labels) if area.labels else [],
            }
            for area in registry.areas.values()
        }
    
    async def _load_entity_registry(self) -> List[Dict[str, Any]]:
        """Load entity registry data."""
        registry = er.async_get(self.hass)
        return [
            {
                "entity_id": entry.entity_id,
                "device_id": entry.device_id,
                "platform": entry.platform,
                "disabled": entry.disabled,
                "area_id": entry.area_id,
                "original_name": entry.original_name,
                "unique_id": entry.unique_id,
                "capabilities": getattr(entry, "capabilities", {}),
                "device_class": getattr(entry, "device_class", None),
                "supported_features": getattr(entry, "supported_features", 0),
            }
            for entry in registry.entities.values()
        ]
    
    async def _load_device_registry(self) -> List[Dict[str, Any]]:
        """Load device registry data."""
        registry = dr.async_get(self.hass)
        return [
            {
                "id": device.id,
                "name": device.name,
                "model": device.model,
                "manufacturer": device.manufacturer,
                "sw_version": device.sw_version,
                "hw_version": device.hw_version,
                "connections": list(device.connections) if device.connections else [],
                "identifiers": list(device.identifiers) if device.identifiers else [],
                "area_id": device.area_id,
                "disabled": device.disabled_by is not None,
                "entry_type": device.entry_type.value if device.entry_type else None,
                "name_by_user": device.name_by_user,
                "configuration_url": getattr(device, "configuration_url", None),
            }
            for device in registry.devices.values()
        ]