# Phase 6.2 — Region & Developer Intelligence

## Goal
Extend the Phase 6.0 shared intelligence model beyond Project dossiers so Region and Developer research views use the same canonical relationship engine.

## Shared engine
Research no longer maintains a second hand-built relationship resolver.

`contextFor(subject)` is now an adapter over:

`IntelligenceContext.query(...)`

The adapter preserves the existing Research UI contract while sourcing:
- projects
- regions
- developers
- infrastructure
- infrastructure schedules
- Legal topic-relevant documents
- Market observations
- listing observations
- articles/events
- selected Macro context

from the shared intelligence model.

## Region Dossier
A Region single-subject view now highlights:
- tracked projects
- selling / ongoing projects
- developer footprint
- direct + geographic Infrastructure context
- regional Market observations
- listing-market price coverage
- topic-relevant Legal documents
- latest linked evidence

Developer chips open the corresponding Developer research dossier.

Infrastructure semantics for a Region include both:
- direct project links
- regional geographic context

Legal evidence remains topic relevance only.

## Developer Dossier
A Developer single-subject view now highlights:
- linked project portfolio
- selling / ongoing projects
- geographic footprint
- project ASP coverage
- listing-market coverage
- portfolio-linked Infrastructure
- topic-relevant Legal documents
- latest linked evidence

Region chips open the corresponding Region research dossier.

Portfolio statistics describe only canonically linked projects. They are not consolidated company financial metrics.

## Cross-module semantics
The following rules remain mandatory:
- Legal topic relevance does not establish legal applicability.
- Regional Market observations are contextual and are not converted into project facts.
- Macro is contextual-only.
- No synthetic scoring/ranking is introduced in Phase 6.2.
- Missing data stays missing.

## Navigation
Region dossier:
- Open regional projects in Market
- Open Infrastructure
- Jump to linked Developer dossier

Developer dossier:
- Open project portfolio in Market
- Jump to linked Region dossier

## Next
Phase **6.3 — Historical Coverage Expansion** increases time-series depth across:
- Listing Market
- quarterly Market research
- Legal lifecycle/amendment history
- Infrastructure milestone/schedule history

After 6.3, Master Phase 6 can be evaluated against its exit criterion.
