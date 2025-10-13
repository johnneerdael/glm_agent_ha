"""Tests for the AreaTopologyService."""

import pytest
from unittest.mock import MagicMock, AsyncMock

from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar, device_registry as dr, entity_registry as er

from custom_components.glm_agent_ha.context.area_topology import AreaTopologyService
from custom_components.glm_agent_ha.context.cache import ContextCacheManager

@pytest.fixture
def mock_hass():
    """Fixture for a mock HomeAssistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.bus = MagicMock()
    return hass

@pytest.fixture
def mock_cache_manager(mock_hass):
    """Fixture for a mock ContextCacheManager."""
    return ContextCacheManager(hass=mock_hass)

@pytest.fixture
async def area_topology_service(mock_hass, mock_cache_manager):
    """Fixture for an AreaTopologyService instance."""
    service = AreaTopologyService(hass=mock_hass, cache_manager=mock_cache_manager)
    
    # Mock the registry loading methods
    mock_cache_manager.get_area_registry = AsyncMock(return_value={
        "living_room": {"area_id": "living_room", "name": "Living Room", "floor_id": "ground_floor", "labels": ["entertainment"]},
        "kitchen": {"area_id": "kitchen", "name": "Kitchen", "floor_id": "ground_floor"},
    })
    mock_cache_manager.get_entity_registry = AsyncMock(return_value=[
        {"entity_id": "light.living_room_main", "area_id": "living_room", "device_id": "dev1", "platform": "mqtt", "disabled": False},
        {"entity_id": "switch.kitchen_socket", "area_id": "kitchen", "device_id": "dev2", "platform": "zha", "disabled": False},
    ])
    mock_cache_manager.get_device_registry = AsyncMock(return_value=[
        {"id": "dev1", "name": "Living Room Lamp", "area_id": "living_room"},
        {"id": "dev2", "name": "Kitchen Socket", "area_id": "kitchen"},
    ])
    
    return service

@pytest.mark.asyncio
async def test_get_floor_summary(area_topology_service: AreaTopologyService):
    """Test the get_floor_summary method."""
    service = await area_topology_service
    summary = await service.get_floor_summary()
    
    assert "ground_floor" in summary
    assert summary["ground_floor"]["area_count"] == 2
    # This test is basic and will be expanded once the test setup is complete.
    # The entity count depends on the full topology build, which is complex to mock initially.
    
@pytest.mark.asyncio
async def test_get_area_topology(area_topology_service: AreaTopologyService):
    """Test the get_area_topology method."""
    service = await area_topology_service
    topology = await service.get_area_topology("living_room")
    
    assert topology is not None
    assert topology.area_id == "living_room"
    assert topology.name == "Living Room"
    assert len(topology.entities) > 0
    assert topology.entities[0].entity_id == "light.living_room_main"
