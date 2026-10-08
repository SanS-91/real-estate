# Phase 5.0 — Cross-Module Research Intelligence

## Goal
Provide one research workspace that starts from a Project, Region or Developer and resolves related canonical data across Market, Infrastructure, Legal, Macro and recent activity.

## Resolution rules
- Project context uses canonical project region, developer, related infrastructure and legal-topic IDs.
- Developer context aggregates only projects explicitly linked to that developer.
- Region context aggregates projects and infrastructure explicitly carrying that region ID.
- Legal documents are surfaced through shared legal topics as research relevance only. This does not determine legal applicability.
- Macro is common market context, not project-specific causality.
- Recent activity uses explicit project/developer/region/infrastructure links from articles and events.

## Safety
- no new business facts are created
- no inferred project pricing, sales or absorption
- no inferred legal applicability
- no project-specific macro causality claim
- canonical registries remain the source of truth
