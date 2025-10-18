---
status: pending
priority: p1
issue_id: "005"
tags: [frontend, javascript, lit-element, bug, critical]
dependencies: []
---

# LitElement connectedCallback Function Error

## Problem Statement
The GLM Agent HA panel is failing to initialize properly due to a TypeError where connectedCallback is not a function. This is breaking the entire frontend functionality.

## Findings
- Location: glm_agent_ha-panel.js:1203, 1251, 1254
- Error: TypeError: (intermediate value).connectedCallback is not a function
- Error: TypeError: this.requestUpdate is not a function
- Frontend is completely broken and unusable
- Panel registration succeeds but component initialization fails

### Scenario Details
1. Panel tries to register with Home Assistant
2. Dependencies not ready, retries panel registration (glm_agent_ha-panel.js:2336)
3. LitElement loads successfully from CDN
4. Panel registration succeeds but connectedCallback fails
5. TypeError thrown at HTMLElement.connectedCallback (glm_agent_ha-panel.js:1203)
6. TypeError thrown at this.requestUpdate (glm_agent_ha-panel.js:1254)
7. Frontend completely non-functional

### Root Cause Analysis
The LitElement component appears to have inheritance or method binding issues. The error suggests that either:
- Component is not properly extending LitElement base class
- connectedCallback method is not properly inherited or bound
- Class definition or prototype chain is broken

## Proposed Solutions

### Option 1: Fix LitElement Class Inheritance
- **Pros**: Properly follows LitElement patterns, resolves core functionality
- **Cons**: Requires understanding of current component structure
- **Effort**: Medium
- **Risk**: Medium

### Option 2: Rewrite Component Using HA Patterns
- **Pros**: Follows Home Assistant frontend conventions, more reliable
- **Cons**: Complete rewrite required
- **Effort**: Large
- **Risk**: High

## Recommended Action
Fix the LitElement component implementation to properly extend the base class and implement connectedCallback correctly. The component appears to have inheritance or method binding issues that need to be resolved.

## Technical Details
- **Affected Files**: glm_agent_ha-panel.js (main frontend component)
- **Related Components**: Entire GLM Agent HA frontend panel
- **Database Changes**: No

## Resources
- Original finding: Frontend browser console errors
- Reference: Home Assistant frontend documentation
- Related issues: WebComponents dependency issue (may be related)

## Acceptance Criteria
- [ ] LitElement component properly extends base class
- [ ] connectedCallback method works correctly
- [ ] this.requestUpdate is available and functional
- [ ] Frontend panel loads without JavaScript errors
- [ ] GLM Agent HA panel becomes fully functional
- [ ] Code reviewed

## Work Log

### 2025-10-18 - Initial Discovery
**By:** Claude Triage System
**Actions:**
- Issue discovered during frontend triage session
- Categorized as P1 (Critical)
- Root cause identified as LitElement inheritance issue
- Estimated effort: Medium (2-4 hours)

**Learnings:**
- Component inheritance issues can completely break frontend functionality
- Proper LitElement patterns are essential for web components
- ConnectedCallback is critical for component lifecycle management

## Notes
Source: Triage session on 2025-10-18
CRITICAL - Frontend is completely broken and unusable without this fix