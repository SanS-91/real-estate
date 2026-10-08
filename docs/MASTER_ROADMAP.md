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
| 4 — Source Registry & Auto Data Collection | IN PROGRESS | Market and Macro have structured collectors; Legal/Infrastructure currently rely mainly on assisted registry-watch/fingerprint discovery. | All four modules have Source → Fetch/Assist → Parse → Normalize → Deduplicate → Candidate paths. |
| 5 — Automation | IN PROGRESS | GitHub Actions, candidate gates, idempotent promotion, source-blocked states and scheduled jobs exist, but operational status is fragmented. | Automatable sources self-refresh; blocked/manual sources are explicit; stale/failure/backlog is visible in one control layer. |
| 6 — Intelligence Database | IN PROGRESS | Market is advanced; Macro has strong historical support; Legal/Infrastructure remain shallower. Project Detail is the first strong cross-module entity view. | Project / Region / Developer / Time can be queried across all four pillars. |
| 7 — Intelligence, Ranking & AI optional | PARTIAL | Research Brief, Watchlist, What Changed and importance fields exist, but no single deterministic ranking engine governs all modules yet. | Rule-based Today / This Week / What Changed / Top Developments exists; AI stays optional and above canonical data. |

## Module architecture audit

| Module | Registry | Collector | Schedule | Candidate gate | Production promotion | History | Intelligence maturity |
|---|---|---|---|---|---|---|---|
| Market | Complete | Complete | Automated + assisted | Complete | Complete | Framework complete; history depth still growing | Advanced |
| Macro | Complete | Complete | Automated | Complete | Complete | Complete | Advanced |
| Legal | Complete | Watch/fingerprint only | Assisted watch | Partial | Manual curated | Framework complete | Partial |
| Infrastructure | Complete | Watch/fingerprint only | Assisted watch | Partial | Manual curated | Framework complete | Partial |

## Main gaps

### Market
- Continue accumulating listing snapshots so history becomes analytically meaningful.
- Expand first-party project updates and research coverage over time.
- Batdongsan.com.vn remains assisted because GitHub-hosted runners are blocked. Do not bypass.

### Macro
- Core architecture is already mature.
- Main remaining need is integration into unified operational health and later cross-module intelligence.

### Legal
Current registry watch can:
- fingerprint canonical pages;
- detect changed pages;
- discover keyword-matched links;
- create a human review queue.

It does **not yet** satisfy the original Phase 4 collector exit criterion.

Required next:
- parse newly discovered official documents;
- normalize document number/title/agency/issued date/effective date/status/topic;
- deduplicate against canonical registry;
- emit candidate records;
- Preview → Promote after review.

### Infrastructure
Current registry watch has the same limitation.

Required next:
- parse official project/milestone updates;
- normalize project, milestone date, schedule revision, investment/status changes;
- append/supersede history rather than overwrite;
- emit candidate records;
- Preview → Promote after review.

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
   - One consolidated status layer for Market / Legal / Infrastructure / Macro.
   - Last successful fetch, last candidate, last promotion, source health, freshness, stale threshold, blocked/manual state, backlog, failure behavior.
   - Goal: close Master Phase 5.

4. **6.0 — Cross-module Intelligence Model**
   - Define shared entity-centric queries:
     - Project
     - Region
     - Developer
     - Time
   - Define cross-module relationship contracts before adding more UI.

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

10. **7.2 — Optional AI Analysis Layer**
    - Summarize.
    - Explain legal impact.
    - Compare projects/developers.
    - Weekly brief.
    - Ask the normalized market database.
    - AI must never become the canonical data source.

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
