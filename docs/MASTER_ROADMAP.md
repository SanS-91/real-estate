# MASTER ROADMAP — Vietnam Real Estate Market Intelligence

Updated: 2026-10-08

This document restores the original 8-phase outline as the governing roadmap. Existing decimal phases (4.5, 5.5F, 5.6A, etc.) are implementation work packages, not replacements for the master phases.

## Original 8-phase status

| Master Phase | Status | Current interpretation | Exit criterion |
|---|---|---|---|
| 0 — Blueprint | COMPLETE | Four pillars, sitemap, static-first architecture, naming and data-flow principles are established. | Architecture is known before feature work. |
| 1 — Skeleton Website | COMPLETE | Home + Market + Legal + Infrastructure + Macro share a responsive shell and reusable UI components. | Site is structurally complete even without deep data. |
| 2 — Data Architecture | COMPLETE | Structured entities, source registry, provenance, observations, articles, relationships and schemas exist across modules. | New data has a canonical place to live. |
| 3 — Simple Data Layer | COMPLETE | Static JSON drives pages, tables, filters, charts, search and history views. | Adding data does not require editing HTML. |
| 4 — Source Registry & Auto Data Collection | COMPLETE | Market, Macro, Legal and Infrastructure now all have structured collection-to-candidate paths with controlled promotion gates. | All four modules have Source → Fetch/Assist → Parse → Normalize → Deduplicate → Candidate → Review/Promote paths. |
| 5 — Automation | COMPLETE | Scheduled collectors, controlled promotion gates, blocked/assisted source states and unified operational health are in place across the four pillars. | Automatable sources self-refresh; blocked/manual sources are explicit; stale/failure/backlog is visible in one control layer. |
| 6 — Intelligence Database | IN PROGRESS | Market is advanced; Macro has strong historical support; Legal/Infrastructure remain shallower. Project Detail is the first strong cross-module entity view. | Project / Region / Developer / Time can be queried across all four pillars. |
| 7 — Intelligence, Ranking & AI optional | COMPLETE | Deterministic attention ranking powers Today / This Week / What Changed / Top Developments; optional AI analysis is available as a disabled-by-default canonical context layer. | Rule-based intelligence surfaces work without AI; AI remains optional and above canonical data. |

## Module architecture audit

| Module | Registry | Collector | Schedule | Candidate gate | Production promotion | History | Intelligence maturity |
|---|---|---|---|---|---|---|---|
| Market | Complete | Complete | Automated + assisted | Complete | Complete | Framework complete; history depth still growing | Advanced |
| Macro | Complete | Complete | Automated | Complete | Complete | Complete | Advanced |
| Legal | Complete | Structured candidate collector | Scheduled + assisted review | Complete | Preview → Promote | Framework complete | Partial |
| Infrastructure | Complete | Structured candidate collector | Scheduled + assisted review | Complete | Preview → Promote | Framework complete | Partial |

## Main gaps

Master Phase 4 is now complete. Remaining collection work is source-coverage expansion and history depth, not missing architecture.

### Market
- Continue accumulating listing snapshots so history becomes analytically meaningful.
- Expand first-party project updates and research coverage over time.
- Batdongsan.com.vn remains assisted because GitHub-hosted runners are blocked. Do not bypass.

### Macro
- Core architecture is already mature.
- Main remaining need is integration into unified operational health and later cross-module intelligence.

### Legal
The structured collector now parses newly discovered official documents into review-required candidates, normalizes metadata, deduplicates against the canonical registry, and uses Preview → Promote for production updates. Remaining work is broader source coverage and deeper amendment/effective-date history.

### Infrastructure
The structured collector now parses official project/milestone updates, proposes explicit project patches, and appends schedule history with supersede semantics through Preview → Promote. Remaining work is broader source coverage and deeper milestone/schedule history.

## Sequential work packages from current state

1. **5.6B — Master Roadmap Alignment & Architecture Audit**
   - Lock this master roadmap.
   - Lock module gap matrix.
   - Add machine-readable roadmap config.
   - No feature expansion.

2. **5.7 — Legal & Infrastructure Collection Completion**
   - Legal structured candidate collector.
   - Infrastructure structured candidate collector.
   - Validation + dedupe + review reports.
   - Preview → Promote gates.
   - Goal: close Master Phase 4.

3. **5.8 — Unified Automation & Data Health**
   - COMPLETE.
   - One consolidated status layer for Market / Legal / Infrastructure / Macro.
   - Workflow health, source/access mode, last successful run, production freshness, candidate backlog and failure behavior are visible from one operations surface.
   - Master Phase 5 is closed.

4. **6.0 — Cross-module Intelligence Model**
   - COMPLETE.
   - Shared entity-centric query contract is defined for Project / Region / Developer / Time.
   - Direct vs contextual evidence semantics are centralized in `IntelligenceContext`.
   - Next: use the shared engine to deepen Project Intelligence without duplicating relationship logic.

5. **6.1 — Project Intelligence Deepening**
   - Complete project dossiers with Market + Legal + Infrastructure + relevant Macro evidence.
   - Use the existing Project Detail page as the base.

6. **6.2 — Region & Developer Intelligence**
   - Region dossier.
   - Developer dossier.
   - Cross-module filters and relationships.

7. **6.3 — Historical Coverage Expansion**
   - More listing snapshots.
   - More quarterly research series.
   - More legal amendment/effective-date history.
   - More infrastructure milestone/schedule history.
   - Goal: close Master Phase 6.

8. **7.0 — Importance & Change Ranking Engine**
   - Deterministic rules based on source quality, freshness, entity relevance, significance and change magnitude.

9. **7.1 — Today / This Week / Top Developments**
   - Derived intelligence surfaces from the ranking engine.
   - No AI required.

10. **7.2 — Optional AI Analysis Layer** — COMPLETE
    - Canonical context packs for summarize / compare / Legal context / weekly brief / Ask database.
    - AI disabled by default; no browser secrets; same-origin server adapter only if explicitly enabled.
    - AI never becomes the canonical data source.

## Architecture principles that remain locked

- Static-first and JSON-first until scale creates a real reason to adopt a database.
- Web pages read normalized data; they do not scrape source sites during page load.
- Missing facts remain missing; do not infer them to fill UI.
- Research houses remain separate sources; do not blend incompatible methodologies.
- Listing asking prices remain separate from official developer/verified pricing.
- Legal-topic links are research shortcuts, not legal-applicability conclusions.
- Infrastructure schedule revisions remain append/supersede history, not destructive overwrite.
- Candidate → Preview → Promote remains the preferred gate for production mutations.
- Blocked sources are marked assisted/blocked instead of bypassed.
- AI is optional analysis above canonical data, not a collection or truth layer.
