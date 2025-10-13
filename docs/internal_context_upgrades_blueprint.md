# Internal Context Upgrades Architecture Blueprint

## 1. Goals & Scope

- Provide the AI agent defined in [`agent.py`](custom_components/glm_agent_ha/agent.py:1) with richer, pre-computed Home Assistant context.
- Reduce repeated registry queries by introducing cached area/floor/entity indexes.
- Expose device diagnostics and energy summaries through dedicated helper APIs.
- Expand automated test coverage to validate new helpers and caching layers.
- Maintain backwards-compatible interfaces for existing services described in [`services.yaml`](custom_components/glm_agent_ha/services.yaml:1).

---

## 2. High-Level Architecture

```mermaid
graph TD
  subgraph Home Assistant Core
    AR[Area Registry]
    ER[Entity Registry]
    DR[Device Registry]
    Recorder[(Recorder DB)]
    States[State Machine]
  end

  subgraph Integration Layer
    CacheMgr[ContextCacheManager]
    AreaSvc[AreaTopologyService]
    DeviceSvc[DeviceDiagnosticsService]
    EnergySvc[EnergySummaryService]
  end

  Agent[AiAgentHaAgent] --> CacheMgr
  Agent --> AreaSvc
  Agent --> DeviceSvc
  Agent --> EnergySvc

  CacheMgr --> AR
  CacheMgr --> ER
  CacheMgr --> DR
  AreaSvc --> CacheMgr
  DeviceSvc --> {States, DR}
  EnergySvc --> {Recorder, States}
```

Key modules (new files or classes):

| Module | Responsibility |
| --- | --- |
| `context/cache.py` (new) | Manage cached snapshots of registries with TTL, invalidation hooks, and selective refresh. |
| `context/area_topology.py` (new) | Build floor→area→entity mappings using cached registries; expose query helpers for agents. |
| `context/device_health.py` (new) | Aggregate diagnostics: battery, connectivity, last-seen timestamps, error attributes. |
| `context/energy_summary.py` (new) | Wrap recorder/statistics queries into standardized energy usage reports. |
| `tests/test_context_*` (new) | Unit/integration coverage for caches, services, and failure modes. |

---

## 3. Detailed Component Designs

### 3.1 `ContextCacheManager`

- **Location**: `custom_components/glm_agent_ha/context/cache.py`
- **Purpose**: Provide reusable caching primitives for registry snapshots.
- **Key responsibilities**:
  - Load area/entity/device registries on demand using async HA helpers.
  - Store results with timestamps; default TTL 300 seconds (configurable via options flow).
  - Offer `await get_or_refresh(key, loader)` utility.
  - Expose invalidation when HA sends registry update events.

**Pseudocode**

```text
class ContextCacheManager:
    def __init__(self, hass, ttl=timedelta(seconds=300)):
        caches = {"area_registry": CacheEntry(...), ...}

    async def get_area_registry(self):
        return await self._get("area_registry", self._load_area_registry)

    async def _load_area_registry(self):
        registry = ar.async_get(self.hass)
        return {area.id: {...}}

    def invalidate(self, key=None):
        # Clear specific or all cached entries
```

- Utilize HA dispatcher signals (`area_registry_updated`, `entity_registry_updated`, etc.) to hook invalidation.

### 3.2 `AreaTopologyService`

- **Location**: `context/area_topology.py`
- **Dependencies**: `ContextCacheManager`
- **Inputs**: cached area, entity, device registries.
- **Outputs**:
  - `get_floor_summary()` → {floor_id: {areas: [...], entity_count: int}}
  - `get_area_entities(area_id)` → list of entity metadata (friendly name, domain, device links).
  - `search_entities_by_label(label)` for user-specific queries.

**Data Model**

```text
AreaTopology = {
  "area_id": str,
  "floor_id": Optional[str],
  "name": str,
  "entities": [EntitySummary],
  "devices": [DeviceSummary]
}
```

- Pre-compute area-to-entity associations by joining entity registry entries with area/device IDs.
- Provide flattening utilities to minimize repeated loops within [`AiAgentHaAgent.get_entities`](custom_components/glm_agent_ha/agent.py:870).

### 3.3 `DeviceDiagnosticsService`

- **Location**: `context/device_health.py`
- **Responsibilities**:
  - Evaluate device health using state attributes (battery level, signal strength) and registry metadata (last_seen, manufacturer).
  - Detect stale devices (compare `state.last_changed` vs. freshness threshold).
  - Provide summary statuses: `OK`, `Warning`, `Critical`.

**APIs**

```text
async def get_device_summary(device_id) -> DeviceHealthReport
async def list_devices_by_status(status) -> List[DeviceHealthReport]
async def get_entities_with_low_battery(threshold=0.2)
```

- Supplement data by inspecting sensor entities associated with the same device (e.g., `battery`, `temperature`).
- Expose aggregated data for agent responses (e.g., “Device Kitchen Sensor battery is at 15%”).

### 3.4 `EnergySummaryService`

- **Location**: `context/energy_summary.py`
- **Responsibilities**:
  - Retrieve energy statistics via recorder API (`statistics.short_term`).
  - Support query windows (24h, 7d) and group-by area or domain.
  - Return normalized objects with consumption, cost (if tariff provided), peak usage times.

**APIs**

```text
async def get_home_energy_summary(hours=24) -> EnergyReport
async def get_area_energy_summary(area_id, hours=24)
async def compare_entity_energy(entity_ids, hours=24)
```

- Use cache to avoid repeated heavy recorder queries; apply TTL ~10 minutes.
- Consider future integration with dedicated energy dashboards.

---

## 4. Integration Points with `AiAgentHaAgent`

### Entry Points to Modify

| Function | Modification |
| --- | --- |
| [`AiAgentHaAgent.__init__`](custom_components_glm_agent_ha/agent.py:687) | Instantiate cache manager and services (area, device, energy). |
| [`get_entities`](custom_components/glm_agent_ha/agent.py:870) | Delegate to `AreaTopologyService` for aggregated lookups. |
| New methods | `async def get_device_diagnostics(...)`, `async def get_energy_summary(...)` to expose new capabilities. |
| `_cache` removal | Replace existing ad-hoc `_cache` dictionary with `ContextCacheManager`. |

- Provide safe fallbacks if services fail (catch exceptions, log warnings, return error dicts per existing conventions).

---

## 5. Configuration & Options

- Extend options flow in [`config_flow.py`](custom_components/glm_agent_ha/config_flow.py:1) to allow:
  - Cache TTL adjustments.
  - Toggles for diagnostics/energy features (for users lacking recorder integration).
- Add constants to [`const.py`](custom_components/glm_agent_ha/const.py:1) for default TTLs, option keys.

---

## 6. Testing Strategy

### Unit Tests (`tests/test_context_cache.py`, etc.)

- Mock HA registry helpers to ensure caches load and invalidate correctly.
- Validate TTL logic and partial invalidation.
- Confirm area topology outputs (floor grouping, entity dedupe).

### Integration Tests (`tests/test_ai_agent_ha/test_context_services.py`)

- Use fixtures in [`tests/conftest.py`](tests/conftest.py:1) to simulate registries and recorder data.
- Ensure `AiAgentHaAgent` integrates new services without breaking existing behaviors.
- Test new agent methods (`get_device_diagnostics`, `get_energy_summary`) via `process_query` flows.

### Performance Considerations

- Benchmark repeated calls to ensure caching reduces load (e.g., measure time difference via mocked time).
- Validate non-blocking behavior (use `async_add_executor_job` only when necessary).

---

## 7. Migration Plan

1. **Phase 0**: Introduce `ContextCacheManager` alongside existing `_cache` usage; gradually pivot methods.
2. **Phase 1**: Implement `AreaTopologyService` and refactor entity lookup methods to use it.
3. **Phase 2**: Add diagnostics and energy services; expose new data request JSON commands (e.g., `"request_type": "get_device_diagnostics"`).
4. **Phase 3**: Update documentation:
   - Blueprint references in [`docs/agent_capability_research.md`](docs/agent_capability_research.md:1).
   - Developer instructions in [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md:1).
5. **Phase 4**: Release candidate with feature flags, monitor logs for performance, adjust TTL defaults.

---

## 8. Open Questions & Future Enhancements

- Should area/floor data be persisted across restarts using `Store` (similar to prompt history)?
- How to gracefully degrade when recorder statistics are unavailable?
- Consider building a local MCP server later that exposes these enriched datasets for agent prompting.
