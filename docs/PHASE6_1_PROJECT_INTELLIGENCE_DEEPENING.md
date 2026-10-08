# Phase 6.1 — Project Intelligence Deepening

## Goal
Turn the existing Project Detail page into the first true cross-module dossier built on the Phase 6.0 shared intelligence contract.

Phase 6.1 does not create new canonical facts. It changes how already-normalized evidence is connected and presented.

## Shared query
Project Detail now queries the shared `IntelligenceContext` engine instead of rebuilding separate relationship logic for every section.

The dossier loads:
- project-level Market observations
- listing-market snapshots
- project-linked articles and events
- directly linked Infrastructure and schedule history
- topic-relevant Legal documents
- region-level Market benchmarks
- selected Macro context

## Evidence semantics

### Direct evidence
Presented as project-linked evidence where a canonical relation exists:
- project Market observations
- listing observations
- Infrastructure project links
- explicit project-linked source articles

### Contextual evidence
Presented separately and never converted into project facts:
- Legal documents linked through controlled project Legal topics
- regional Market benchmarks
- Macro indicators

Legal topic relevance does not establish legal applicability.

Macro conditions are broad context only.

## Project Detail changes

### Intelligence Coverage
A new coverage panel summarizes how much evidence is currently available across:
- verified Market observations
- listing snapshots
- Infrastructure
- Legal topic relevance
- regional benchmarks
- Macro series

### Legal Research
The page now surfaces recent canonical Legal documents matching the project's controlled Legal topics, while preserving the applicability disclaimer.

### Infrastructure
Infrastructure links now include latest available schedule/milestone context from the canonical schedules dataset.

### Regional Market & Macro Context
A dedicated contextual section shows:
- recent region-level Market observations
- selected latest Macro indicators

These rows are explicitly labelled contextual.

## Data loading
Market keeps its existing Market-only news behavior while Project Detail also loads the full cross-module article dataset for the shared intelligence query.

## Next
Phase **6.2 — Region & Developer Intelligence** reuses the same `IntelligenceContext` contract to create comparable dossiers for Regions and Developers without copying Project-specific relationship logic.
