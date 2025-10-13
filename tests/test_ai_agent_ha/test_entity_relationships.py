"""Tests for the EntityRelationshipService."""

import pytest
from unittest.mock import MagicMock, AsyncMock

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import EntityRegistry, RegistryEntry
from homeassistant.helpers.device_registry import DeviceRegistry, DeviceEntry
from homeassistant.helpers.area_registry import AreaRegistry, AreaEntry

from custom_components.glm_agent_ha.context.cache import ContextCacheManager
from custom_components.glm_agent_ha.context.entity_relationships import EntityRelationshipService

@pytest.fixture
def mock_area_registry():
    """Fixture for a mock Area Registry."""
    registry = MagicMock(spec=AreaRegistry)
    registry.areas = {}
    return registry

@pytest.fixture
def mock_hass():
    """Fixture for a mock Home Assistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    hass.helpers = MagicMock()
    return hass

@pytest.fixture
def mock_entity_registry():
    """Fixture for a mock Entity Registry."""
    registry = MagicMock(spec=EntityRegistry)
    registry.entities = {}
    return registry

@pytest.fixture
def mock_device_registry():
    """Fixture for a mock Device Registry."""
    registry = MagicMock(spec=DeviceRegistry)
    registry.devices = {}
    return registry

@pytest.fixture
def mock_cache_manager():
    """Fixture for a mock ContextCacheManager."""
    mock_manager = MagicMock(spec=ContextCacheManager)
    mock_manager.get_or_refresh.return_value = None
    mock_manager.store = MagicMock()
    return mock_manager

@pytest.fixture
async def entity_relationship_service(mock_hass, mock_cache_manager, mock_entity_registry, mock_device_registry, mock_area_registry):
    """Fixture for an initialized EntityRelationshipService."""
    
    # Place mock registries into hass.data as the real async_get would expect
    mock_hass.data['entity_registry'] = mock_entity_registry
    mock_hass.data['device_registry'] = mock_device_registry
    mock_hass.data['area_registry'] = mock_area_registry

    service = EntityRelationshipService(hass=mock_hass, cache=mock_cache_manager, enabled=True)
    
    # Mock some registry entries
    mock_entity_registry.entities['light.living_room'] = RegistryEntry(
        entity_id='light.living_room',
        unique_id='lr_light_1',
        platform='test',
        device_id='device_1',
        area_id='living_room'
    )
    mock_entity_registry.entities['switch.fan'] = RegistryEntry(
        entity_id='switch.fan',
        unique_id='fan_switch_1',
        platform='test',
        device_id='device_2',
        area_id='living_room'
    )
    mock_entity_registry.entities['sensor.temperature'] = RegistryEntry(
        entity_id='sensor.temperature',
        unique_id='temp_sensor_1',
        platform='test',
        device_id='device_1',
        area_id='living_room'
    )
    mock_entity_registry.entities['binary_sensor.door'] = RegistryEntry(
        entity_id='binary_sensor.door',
        unique_id='door_sensor_1',
        platform='test',
        device_id='device_3',
        area_id='entryway'
    )

    mock_device_registry.devices['device_1'] = DeviceEntry(
        id='device_1',
        config_entries=set(),
        connections=set(),
        identifiers=set(),
        manufacturer='Test Inc.',
        model='SmartDevice',
        name='Living Room Smart Device',
        area_id='living_room'
    )
    mock_device_registry.devices['device_2'] = DeviceEntry(
        id='device_2',
        config_entries=set(),
        connections=set(),
        identifiers=set(),
        manufacturer='Test Inc.',
        model='SmartFan',
        name='Living Room Fan',
        area_id='living_room'
    )
    mock_device_registry.devices['device_3'] = DeviceEntry(
        id='device_3',
        config_entries=set(),
        connections=set(),
        identifiers=set(),
        manufacturer='SecureCorp',
        model='DoorSensor',
        name='Front Door Sensor',
        area_id='entryway'
    )

    mock_area_registry.areas['living_room'] = AreaEntry(
        id='living_room',
        name='Living Room',
        normalized_name='living_room',
        aliases=set(),
    )
    mock_area_registry.areas['entryway'] = AreaEntry(
        id='entryway',
        name='Entryway',
        normalized_name='entryway',
        aliases=set(),
    )

    await service.build_relationship_maps()
    return service

@pytest.mark.asyncio
async def test_get_entities_by_category(entity_relationship_service: EntityRelationshipService):
    """Test getting entities by category."""
    service = await entity_relationship_service
    lighting_entities = await service.get_entities_by_category('lighting')
    assert 'light.living_room' in lighting_entities

    climate_entities = await service.get_entities_by_category('climate')
    assert 'switch.fan' in climate_entities
    assert 'sensor.temperature' in climate_entities

    security_entities = await service.get_entities_by_category('security')
    assert 'binary_sensor.door' in security_entities

@pytest.mark.asyncio
async def test_get_related_entities(entity_relationship_service: EntityRelationshipService):
    """Test getting related entities."""
    service = await entity_relationship_service
    related_to_light = await service.get_related_entities('light.living_room')
    
    assert 'sensor.temperature' in related_to_light
    assert 'switch.fan' in related_to_light

    related_to_door = await service.get_related_entities('binary_sensor.door')
    assert not related_to_door