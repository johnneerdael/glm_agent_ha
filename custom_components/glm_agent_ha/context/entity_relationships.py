"""Entity relationship mapping and discovery service.

This service provides intelligent entity discovery, relationship mapping,
and categorization capabilities for the AI agent.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import defaultdict

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import area_registry as ar

from .cache import ContextCacheManager

_LOGGER = logging.getLogger(__name__)


class EntityRelationshipService:
    """Service for mapping and discovering entity relationships."""

    def __init__(
        self, 
        hass: HomeAssistant, 
        cache: ContextCacheManager,
        enabled: bool = True
    ):
        """Initialize the entity relationship service."""
        self.hass = hass
        self.cache = cache
        self.enabled = enabled
        
        # Relationship mappings
        self._device_to_entities: Dict[str, List[str]] = {}
        self._area_to_devices: Dict[str, List[str]] = {}
        self._entity_relationships: Dict[str, Dict[str, Any]] = {}
        self._domain_categories: Dict[str, List[str]] = {}
        
        # Cache keys
        self._CACHE_KEYS = {
            "device_to_entities": "entity_relationships_device_to_entities",
            "area_to_devices": "entity_relationships_area_to_devices", 
            "entity_relationships": "entity_relationships_mapping",
            "domain_categories": "entity_relationships_domain_categories"
        }

    async def build_relationship_maps(self) -> None:
        """Build comprehensive relationship maps between entities, devices, and areas."""
        if not self.enabled:
            return
            
        _LOGGER.debug("Building entity relationship maps")
        
        try:
            # Get registries
            entity_registry = er.async_get(self.hass)
            device_registry = dr.async_get(self.hass)
            area_registry = ar.async_get(self.hass)
            
            # Build device to entities mapping
            await self._build_device_to_entities_map(entity_registry)
            
            # Build area to devices mapping
            await self._build_area_to_devices_map(device_registry, area_registry)
            
            # Build entity relationships
            await self._build_entity_relationships(entity_registry, device_registry)
            
            # Build domain categories
            await self._build_domain_categories()
            
            _LOGGER.debug("Entity relationship maps built successfully")
            
        except Exception as e:
            _LOGGER.exception("Error building relationship maps: %s", str(e))

    async def _build_device_to_entities_map(self, entity_registry) -> None:
        """Build mapping from devices to their entities."""
        cache_key = self._CACHE_KEYS["device_to_entities"]
        cached_data = await self.cache.get_or_refresh(cache_key, lambda: None)
        if cached_data is not None:
            self._device_to_entities = cached_data
            return

        device_to_entities = defaultdict(list)
        
        for entity in entity_registry.entities.values():
            if entity.device_id:
                device_to_entities[entity.device_id].append(entity.entity_id)
        
        self._device_to_entities = dict(device_to_entities)
        self.cache.store(cache_key, self._device_to_entities)

    async def _build_area_to_devices_map(self, device_registry, area_registry) -> None:
        """Build mapping from areas to their devices."""
        cache_key = self._CACHE_KEYS["area_to_devices"]
        cached_data = await self.cache.get_or_refresh(cache_key, lambda: None)
        if cached_data is not None:
            self._area_to_devices = cached_data
            return

        area_to_devices = defaultdict(list)
        
        for device in device_registry.devices.values():
            if device.area_id:
                area_to_devices[device.area_id].append(device.id)
        
        self._area_to_devices = dict(area_to_devices)
        self.cache.store(cache_key, self._area_to_devices)

    async def _build_entity_relationships(self, entity_registry, device_registry) -> None:
        """Build comprehensive entity relationship mapping."""
        cache_key = self._CACHE_KEYS["entity_relationships"]
        cached_data = await self.cache.get_or_refresh(cache_key, lambda: None)
        if cached_data is not None:
            self._entity_relationships = cached_data
            return

        relationships = {}
        
        for entity in entity_registry.entities.values():
            entity_id = entity.entity_id
            domain = entity_id.split(".")[0]
            
            relationships[entity_id] = {
                "domain": domain,
                "device_id": entity.device_id,
                "area_id": entity.area_id,
                "original_name": entity.original_name,
                "unique_id": entity.unique_id,
                "platform": entity.platform,
                "disabled": entity.disabled,
                "related_entities": [],
                "related_devices": [],
                "related_areas": []
            }
            
            # Add device relationships
            if entity.device_id:
                relationships[entity_id]["related_devices"].append(entity.device_id)
                related_entities = self._device_to_entities.get(entity.device_id, [])
                relationships[entity_id]["related_entities"] = [
                    e for e in related_entities if e != entity_id
                ]
            
            # Add area relationships (direct and via device)
            related_areas = set()
            if entity.area_id:
                related_areas.add(entity.area_id)
            
            if entity.device_id:
                device = device_registry.devices.get(entity.device_id)
                if device and device.area_id:
                    related_areas.add(device.area_id)
            
            relationships[entity_id]["related_areas"] = list(related_areas)
        
        self._entity_relationships = relationships
        self.cache.store(cache_key, self._entity_relationships)

    async def _build_domain_categories(self) -> None:
        """Build domain categorization with intelligent groupings."""
        cache_key = self._CACHE_KEYS["domain_categories"]
        cached_data = await self.cache.get_or_refresh(cache_key, lambda: None)
        if cached_data is not None:
            self._domain_categories = cached_data
            return

        # Define intelligent domain categories
        domain_categories = {
            "lighting": ["light"],
            "climate": ["climate", "humidifier", "air_purifier", "air_quality", "switch", "sensor"],
            "security": ["binary_sensor", "camera", "alarm_control_panel", "lock"],
            "sensors": ["sensor", "update"],
            "switches": ["switch", "input_boolean"],
            "covers": ["cover", "garage_door", "blinds"],
            "media": ["media_player", "remote", "tv", "receiver"],
            "appliances": ["vacuum", "washing_machine", "dishwasher", "dryer"],
            "energy": ["energy", "power", "electric", "gas", "water"],
            "automation": ["automation", "script", "scene"],
            "network": ["router", "switch", "modem", "wifi"],
            "computing": ["computer", "server", "nas"],
            "weather": ["weather", "sun"],
            "location": ["person", "device_tracker", "zone"],
            "calendar": ["calendar"],
            "notification": ["notify", "mobile_app", "persistent_notification"]
        }
        
        self._domain_categories = domain_categories
        self.cache.store(cache_key, self._domain_categories)

    async def get_entities_by_category(self, category: str) -> List[str]:
        """Get all entities belonging to a specific category."""
        if not self.enabled or category not in self._domain_categories:
            return []
        
        domains = self._domain_categories[category]
        entities = []
        
        for domain in domains:
            domain_entities = [eid for eid in self._entity_relationships.keys() 
                              if eid.startswith(f"{domain}.")]
            entities.extend(domain_entities)
        
        return entities

    async def get_related_entities(self, entity_id: str, relationship_type: str = "all") -> List[str]:
        """Get entities related to a specific entity."""
        if not self.enabled or entity_id not in self._entity_relationships:
            return []
        
        entity_rels = self._entity_relationships[entity_id]
        related = []
        
        if relationship_type in ["all", "entities"]:
            related.extend(entity_rels.get("related_entities", []))
        
        if relationship_type in ["all", "areas"]:
            # Get entities in related areas
            for area_id in entity_rels.get("related_areas", []):
                area_entities = await self._get_entities_in_area(area_id)
                related.extend(area_entities)
        
        if relationship_type in ["all", "devices"]:
            # Get entities on related devices
            for device_id in entity_rels.get("related_devices", []):
                device_entities = self._device_to_entities.get(device_id, [])
                related.extend(device_entities)
        
        # Remove duplicates and the original entity
        return list(set(related) - {entity_id})

    async def _get_entities_in_area(self, area_id: str) -> List[str]:
        """Get all entities in a specific area."""
        entities = []
        
        # Get devices in area
        devices = self._area_to_devices.get(area_id, [])
        
        # Get entities for those devices
        for device_id in devices:
            device_entities = self._device_to_entities.get(device_id, [])
            entities.extend(device_entities)
        
        # Get entities directly assigned to area
        for entity_id, entity_rels in self._entity_relationships.items():
            if area_id in entity_rels.get("related_areas", []):
                entities.append(entity_id)
        
        return list(set(entities))

    async def get_entity_categories(self, entity_id: str) -> List[str]:
        """Get all categories a specific entity belongs to."""
        if not self.enabled or entity_id not in self._entity_relationships:
            return []
        
        domain = entity_id.split(".")[0]
        categories = []
        
        for category, domains in self._domain_categories.items():
            if domain in domains:
                categories.append(category)
        
        return categories

    async def find_entities_by_attributes(self, **attributes) -> List[str]:
        """Find entities matching specific attributes."""
        if not self.enabled:
            return []
        
        matching_entities = []
        
        for entity_id, entity_rels in self._entity_relationships.items():
            match = True
            
            for attr_name, attr_value in attributes.items():
                if attr_name == "domain" and entity_rels["domain"] != attr_value:
                    match = False
                    break
                elif attr_name == "area_id" and attr_value not in entity_rels["related_areas"]:
                    match = False
                    break
                elif attr_name == "device_id" and entity_rels["device_id"] != attr_value:
                    match = False
                    break
                elif attr_name == "category":
                    entity_categories = await self.get_entity_categories(entity_id)
                    if attr_value not in entity_categories:
                        match = False
                        break
            
            if match:
                matching_entities.append(entity_id)
        
        return matching_entities

    async def get_device_hierarchy(self, device_id: str) -> Dict[str, Any]:
        """Get hierarchical information for a device."""
        if not self.enabled:
            return {}
        
        entities = self._device_to_entities.get(device_id, [])
        areas = set()
        
        # Get areas from device and entities
        for entity_id in entities:
            if entity_id in self._entity_relationships:
                entity_areas = self._entity_relationships[entity_id].get("related_areas", [])
                areas.update(entity_areas)
        
        return {
            "device_id": device_id,
            "entities": entities,
            "areas": list(areas),
            "entity_count": len(entities),
            "area_count": len(areas)
        }

    async def invalidate_cache(self) -> None:
        """Invalidate all relationship caches."""
        for cache_key in self._CACHE_KEYS.values():
            self.cache.delete(cache_key)
        
        # Clear in-memory mappings
        self._device_to_entities.clear()
        self._area_to_devices.clear()
        self._entity_relationships.clear()
        self._domain_categories.clear()
        
        _LOGGER.debug("Entity relationship caches invalidated")