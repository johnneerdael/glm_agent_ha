"""Area topology service for GLM Agent HA integration."""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

from homeassistant.core import HomeAssistant

from .cache import ContextCacheManager

_LOGGER = logging.getLogger(__name__)


@dataclass
class EntitySummary:
    """Summary of an entity for topology queries."""
    
    entity_id: str
    friendly_name: Optional[str]
    domain: str
    device_class: Optional[str]
    area_id: Optional[str]
    device_id: Optional[str]
    platform: str
    disabled: bool
    capabilities: Dict[str, Any]
    supported_features: int


@dataclass
class DeviceSummary:
    """Summary of a device for topology queries."""
    
    device_id: str
    name: Optional[str]
    model: Optional[str]
    manufacturer: Optional[str]
    area_id: Optional[str]
    disabled: bool
    entry_type: Optional[str]


@dataclass
class AreaTopology:
    """Topology information for an area."""
    
    area_id: str
    floor_id: Optional[str]
    name: str
    entities: List[EntitySummary]
    devices: List[DeviceSummary]
    labels: List[str]


class AreaTopologyService:
    """Service for building and querying area/floor/entity topology."""
    
    def __init__(self, hass: HomeAssistant, cache_manager: ContextCacheManager, enabled: bool = True):
        """Initialize the area topology service."""
        self.hass = hass
        self.cache_manager = cache_manager
        self.enabled = enabled
        self._entity_to_area: Dict[str, str] = {}
        self._area_to_entities: Dict[str, List[str]] = {}
        self._floor_to_areas: Dict[str, List[str]] = {}
    
    async def get_floor_summary(self) -> Dict[str, Dict[str, Any]]:
        """Get summary of all floors with their areas and entity counts."""
        return await self.cache_manager.get_or_refresh(
            "floor_summary",
            self._build_floor_summary,
        )
    
    async def get_area_topology(self, area_id: str) -> Optional[AreaTopology]:
        """Get topology information for a specific area."""
        topologies = await self.get_all_area_topologies()
        return topologies.get(area_id)
    
    async def get_all_area_topologies(self) -> Dict[str, AreaTopology]:
        """Get topology information for all areas."""
        return await self.cache_manager.get_or_refresh(
            "area_topologies",
            self._build_area_topologies,
        )
    
    async def get_area_entities(self, area_id: str) -> List[EntitySummary]:
        """Get all entities in a specific area."""
        topology = await self.get_area_topology(area_id)
        return topology.entities if topology else []
    
    async def get_floor_entities(self, floor_id: str) -> List[EntitySummary]:
        """Get all entities on a specific floor."""
        floor_summary = await self.get_floor_summary()
        floor_areas = floor_summary.get(floor_id, {}).get("areas", [])
        
        all_entities = []
        for area_id in floor_areas:
            entities = await self.get_area_entities(area_id)
            all_entities.extend(entities)
        
        return all_entities
    
    async def search_entities_by_label(self, label: str) -> List[EntitySummary]:
        """Find entities associated with a specific label."""
        topologies = await self.get_all_area_topologies()
        matching_entities = []
        
        for topology in topologies.values():
            if label in topology.labels:
                matching_entities.extend(topology.entities)
        
        return matching_entities
    
    async def get_entity_area(self, entity_id: str) -> Optional[str]:
        """Get the area ID for a specific entity."""
        # Build entity-to-area mapping if not cached
        if not self._entity_to_area:
            await self._build_entity_mappings()
        
        return self._entity_to_area.get(entity_id)
    
    async def get_entities_by_filter(
        self,
        domains: Optional[List[str]] = None,
        device_classes: Optional[List[str]] = None,
        area_ids: Optional[List[str]] = None,
        floor_id: Optional[str] = None,
        include_disabled: bool = False,
    ) -> List[EntitySummary]:
        """Get entities matching specific filters."""
        # Start with all entities
        topologies = await self.get_all_area_topologies()
        all_entities = []
        for topology in topologies.values():
            all_entities.extend(topology.entities)
        
        # Apply filters
        filtered_entities = []
        for entity in all_entities:
            # Skip disabled unless explicitly included
            if not include_disabled and entity.disabled:
                continue
            
            # Domain filter
            if domains and entity.domain not in domains:
                continue
            
            # Device class filter
            if device_classes and entity.device_class not in device_classes:
                continue
            
            # Area filter
            if area_ids and entity.area_id not in area_ids:
                continue
            
            # Floor filter
            if floor_id:
                topology = await self.get_area_topology(entity.area_id) if entity.area_id else None
                if not topology or topology.floor_id != floor_id:
                    continue
            
            filtered_entities.append(entity)
        
        return filtered_entities
    
    async def _build_floor_summary(self) -> Dict[str, Dict[str, Any]]:
        """Build summary of floors and their areas."""
        area_registry = await self.cache_manager.get_area_registry()
        floor_summary: Dict[str, Dict[str, Any]] = {}
        
        for area_data in area_registry.values():
            floor_id = area_data.get("floor_id")
            if floor_id is None:
                floor_id = "no_floor"
            
            if floor_id not in floor_summary:
                floor_summary[floor_id] = {
                    "areas": [],
                    "entity_count": 0,
                    "area_count": 0,
                }
            
            floor_summary[floor_id]["areas"].append(area_data["area_id"])
            floor_summary[floor_id]["area_count"] += 1
        
        # Count entities per floor
        topologies = await self.get_all_area_topologies()
        for area_id, topology in topologies.items():
            floor_id = topology.floor_id or "no_floor"
            floor_summary[floor_id]["entity_count"] += len(topology.entities)
        
        return floor_summary
    
    async def _build_area_topologies(self) -> Dict[str, AreaTopology]:
        """Build topology information for all areas."""
        area_registry = await self.cache_manager.get_area_registry()
        entity_registry = await self.cache_manager.get_entity_registry()
        device_registry = await self.cache_manager.get_device_registry()
        
        # Build device lookup
        device_lookup = {device["id"]: device for device in device_registry}
        
        # Build entity lookup and mappings
        entity_lookup = {entity["entity_id"]: entity for entity in entity_registry}
        
        # Build area topologies
        topologies: Dict[str, AreaTopology] = {}
        
        for area_id, area_data in area_registry.items():
            entities = []
            devices = []
            
            # Find entities in this area
            for entity_data in entity_registry:
                if entity_data.get("area_id") == area_id:
                    # Check if entity is assigned via device
                    device_id = entity_data.get("device_id")
                    if device_id:
                        device = device_lookup.get(device_id)
                        if device and device.get("area_id") == area_id:
                            # Entity is in area via device
                            entity_summary = self._create_entity_summary(entity_data)
                            entities.append(entity_summary)
                            
                            # Add device if not already added
                            if not any(d["device_id"] == device_id for d in devices):
                                devices.append(device)
                    else:
                        # Entity is directly assigned to area
                        entity_summary = self._create_entity_summary(entity_data)
                        entities.append(entity_summary)
            
            # Create topology
            topology = AreaTopology(
                area_id=area_id,
                floor_id=area_data.get("floor_id"),
                name=area_data["name"],
                entities=entities,
                devices=devices,
                labels=area_data.get("labels", []),
            )
            topologies[area_id] = topology
        
        return topologies
    
    def _create_entity_summary(self, entity_data: Dict[str, Any]) -> EntitySummary:
        """Create an entity summary from registry data."""
        return EntitySummary(
            entity_id=entity_data["entity_id"],
            friendly_name=entity_data.get("original_name"),
            domain=entity_data["entity_id"].split(".")[0],
            device_class=entity_data.get("device_class"),
            area_id=entity_data.get("area_id"),
            device_id=entity_data.get("device_id"),
            platform=entity_data["platform"],
            disabled=entity_data["disabled"],
            capabilities=entity_data.get("capabilities", {}),
            supported_features=entity_data.get("supported_features", 0),
        )
    
    async def _build_entity_mappings(self) -> None:
        """Build entity-to-area and area-to-entity mappings."""
        topologies = await self.get_all_area_topologies()
        
        self._entity_to_area.clear()
        self._area_to_entities.clear()
        
        for area_id, topology in topologies.items():
            entity_ids = [entity.entity_id for entity in topology.entities]
            self._area_to_entities[area_id] = entity_ids
            
            for entity_id in entity_ids:
                self._entity_to_area[entity_id] = area_id
    
    def invalidate_cache(self) -> None:
        """Invalidate topology cache."""
        self.cache_manager.invalidate("area_topologies")
        self.cache_manager.invalidate("floor_summary")
        self._entity_to_area.clear()
        self._area_to_entities.clear()
        self._floor_to_areas.clear()
        _LOGGER.debug("Invalidated area topology cache")