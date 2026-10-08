# Phase 6.0 — Cross-module Intelligence Model

## Goal
Start Master Phase 6 by defining one shared intelligence contract for the four canonical query dimensions:

- Project
- Region
- Developer
- Time

This phase is intentionally model-first. It does not add a new dashboard.

## Shared relationship model
`config/intelligence_model.json` defines:
- canonical subject datasets
- direct relationship fields
- evidence datasets
- date fields
- time-window rules
- direct vs contextual semantics

`assets/js/intelligence-context.js` implements the contract for browser-side queries.

## Direct vs contextual evidence
The engine deliberately separates two evidence classes.

### Direct
The source record carries an explicit canonical link.

Examples:
- listing snapshot → project_id
- project observation → project_id
- infrastructure project → related_real_estate_project_ids
- article → project_ids / developer_ids

### Contextual
The record is relevant through a controlled shared context but must not be presented as a direct entity fact.

Examples:
- region-level market benchmark shown beside a project
- Legal documents connected through project legal topics
- Macro observations shown as broad context

## Legal semantics
Project → legal topic → legal document is **topic relevance only**.

It is a research shortcut and never means that a Legal document is automatically applicable to a specific project.

## Macro semantics
Macro evidence is opt-in and contextual-only.

The engine does not attach interest rates, FX, CPI, credit or gold to a project as project facts.

## Time contract
Queries accept:
- `from`
- `to`

Bounds are inclusive.

Supported period normalization:
- YYYY-MM-DD
- YYYY-MM
- YYYY-Qn
- YYYY

Rows without a usable date remain valid in the entity dataset but are excluded from a bounded time-evidence query.

## Engine API
`IntelligenceContext.contextFor(data, type, id)`

Resolves the shared entity relationship set.

`IntelligenceContext.query(data, request)`

Returns:
- subject
- time window
- resolved IDs
- direct evidence
- contextual evidence
- relationship semantics

## Referential integrity
Phase 6.0 tests verify:
- every project Region ID exists
- every project Developer ID exists
- every project Legal Topic ID exists
- every related Infrastructure ID exists
- every Infrastructure related Project ID exists
- every evidence dataset configured by the model exists

## Next
Phase **6.1 — Project Intelligence Deepening** uses this engine to refactor/strengthen Project Detail into a true cross-module dossier without duplicating relationship logic.
