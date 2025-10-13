# Registry & Entity Discovery Capability Plan

## 1. Objective

Enhance the internal context available to [`AiAgentHaAgent`](custom_components/glm_agent_ha/agent.py:474) by delivering richer, low-latency insights derived from the Home Assistant registries. The goal is to minimize multi-call loops, improve entity discovery accuracy, and unlock higher-quality automations and dashboards without relying on external MCP providers.

## 2. Current Baseline

- Registry access flows already exist (`get_area_registry`, `get_entity_registry`, `get_device_registry`) but return raw snapshots with minimal shaping.
- Entity lookup helpers (`get_entities`, `get_entities_by_area`) repeatedly traverse registries, incurring redundant joins and inconsistent metadata.
- Prompt instructions in [`agent.py`](custom_components_glm_agent_ha/agent.py:478) emphasize manual command patterns because higher-level abstractions are missing.
- No persistent indexing or search facilities exist for floors, labels, device classes, or entity capabilities.

## 3. Proposed Capabilities (Prioritized)

| Priority | Capability | Description | Agent Impact |
| --- | --- | --- | --- |
| P0 | **Area-Floor Topology Index** | Pre-compute floor→area→entity mappings with cached joins across registries. Provide fast lookups and metadata-rich summaries. | Eliminates ad-hoc loops in `get_entities`, supports floor-based prompts. |
| P0 | **Entity Capability Catalog** | Normalize entity metadata (domain, device class, suggested actions, available services) and expose targeted search helpers. | Enables accurate service recommendations and automation scaffolding. |
| P1 | **Label & Tag Resolver** | Surface label-based entity groups (e.g. “critical devices”, “upstairs”) with support for user-defined tags. | Improves user intent matching for natural-language queries referencing labels. |
| P1 | **Device Health Snapshot** | Aggregate battery levels, connectivity, last_seen, and diagnostic sensors per device. | Allows proactive maintenance suggestions and better validation before automation creation. |
| P2 | **History & Usage Prefetch** | Cache lightweight statistics (recent toggles, average runtime) for frequently-requested entities. | Supplies richer context for dashboards and automation condition recommendations. |
| P2 | **Entity Search DSL** | Introduce structured search API (filters for domain, device class, area, availability, custom predicates). | Simplifies prompt engineering and reduces reliance on free-form instructions. |

## 4. Implementation Backlog

1. **ContextCacheManager Foundation (Dependency)**
   - Implement shared cache in `context/cache.py` (see [`docs/internal_context_upgrades_blueprint.md`](docs/internal_context_upgrades_blueprint.md:57)).
   - Subscribe to registry update signals for invalidation.

2. **Area Topology & Capability Catalog (P0)**
   - Add `AreaTopologyService` (area/floor maps, entity summaries).
   - Build `EntityCapabilityCatalog` (new module) to normalize metadata and expose APIs:
     - `list_entities(filters)` for filtered discovery.
     - `describe_entity(entity_id)` returning services, attributes, diagnostic hints.
   - Refactor [`AiAgentHaAgent.get_entities`](custom_components_glm_agent_ha/agent.py:870) to leverage the new services.

3. **Label & Tag Resolver (P1)**
   - Extend topology data model to include labels (from `AreaEntry.labels` and entity custom attributes).
   - Provide helper methods for label queries:
     - `find_entities_by_label(label_name)`
     - `list_labels(scope)` (area/device/entity).

4. **Device Health Snapshot (P1)**
   - Implement `DeviceDiagnosticsService` as outlined in the blueprint.
   - Map device health states into discrete buckets (`OK`, `Warning`, `Critical`) and include remediation hints.

5. **History & Usage Prefetch (P2)**
   - Define lightweight summary jobs utilizing recorder statistics with configurable TTL.
   - Store results in cache to support quick retrieval for entity usage questions.

6. **Entity Search DSL (P2)**
   - Design simple filter schema (domain, area_ids, device_class, availability, label).
   - Provide serialization helpers so the agent can request searches through structured JSON.

## 5. Integration & API Surface

- Update the agent’s data-request handling (within `process_query`) to support new request types:
  - `get_area_topology`, `get_entities_by_capability`, `get_entities_by_label`, `get_device_diagnostics`.
- Maintain backward compatibility by falling back to legacy helpers when new services are disabled.

## 6. Testing & Validation

- Create dedicated unit tests under `tests/test_context_*` for each new service.
- Expand integration coverage:
  - Validate `process_query` can execute end-to-end flows using the new helpers.
  - Include performance assertions (mocked time) to ensure caching reduces repeated lookups.

## 7. Documentation & Rollout

- Document usage patterns and API contracts in [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md:1).
- Provide release notes summarizing capability improvements and configuration toggles.
- Coordinate with future MCP plans so the enriched context can later be exposed through a local MCP server if desired.

## 8. Risks & Mitigations

- **Cache staleness**: rely on HA dispatcher signals and short TTL defaults.
- **Recorder dependency**: feature-gate history/usage prefetch when recorder is unavailable.
- **Performance**: benchmark registry indexing on startup and guard with async executor usage for heavy joins.

## 9. Next Steps

1. Implement and land `ContextCacheManager` alongside `AreaTopologyService` (P0).
2. Refactor agent entity discovery pathways to use the new topology and capability catalog.
3. Iterate on diagnostics and labeling features (P1) once baseline services are stable.
4. Revisit P2 enhancements after validating performance and accuracy gains from P0/P1 work.
