# Vietnam Real Estate Market Intelligence

Implementation v1 is being built sequentially as a static-first research webapp for GitHub Pages.

## Current implementation status

The original **8-phase master roadmap (Phase 0 → 7)** remains the governing plan. Decimal phases such as 5.5F or 5.6A are implementation work packages under that master roadmap.

Current master status:
- Phase 0 — Blueprint: complete.
- Phase 1 — Skeleton Website: complete.
- Phase 2 — Data Architecture: complete.
- Phase 3 — Simple Data Layer: complete.
- Phase 4 — Source Registry & Auto Data Collection: complete; all four pillars now have structured collection-to-candidate paths with controlled promotion gates.
- Phase 5 — Automation: in progress; unified operational health/stale/backlog visibility remains to be completed.
- Phase 6 — Intelligence Database: in progress; Market is the most mature module and Project Detail is the first deep entity view.
- Phase 7 — Intelligence / Ranking / optional AI: partial.

See `docs/MASTER_ROADMAP.md` and `config/master-roadmap.json` for the authoritative roadmap, module audit, exit criteria and sequential next work packages.

- Step 1 — Repository skeleton, shared shell and responsive design system: complete.
- Step 2 — Home dashboard skeleton and shared content components: complete.
- Step 3 — Market module: complete.
- Step 4 — Legal module: complete.
- Step 5 — Infrastructure module: complete.
- Step 6 — Macro module: complete.
- Step 7 — Global structured search and final frontend integration: complete.
- Current data is hybrid: Market / Legal / Infrastructure registries are curated source-backed datasets; Macro overlays controlled production observations on the legacy static frontend dataset.
- Illustrative/demo records are retained only where a module or evidence layer has not yet been promoted to curated/production status. Missing facts are not inferred.

## Run locally

Because the app loads JSON with `fetch()`, do not open `index.html` directly with `file://`.

From the repository root, run a local web server, for example:

```bash
python -m http.server 8000
```

Then open:

```text
http://localhost:8000/
```

## GitHub Pages

The repository is compatible with GitHub Pages using the `main` branch and `/ (root)` publishing folder.

## Data mode

`config/settings.json` still points to the historical static root:

```text
./data/mock/
```

The folder name is retained for frontend compatibility and no longer means that every record inside it is mock data. Current classification is:

- Market: curated project/developer registry and curated research benchmarks.
- Legal: curated official-document registry.
- Infrastructure: curated official/project-source registry with schedule history.
- Macro: hybrid; indicator definitions and fallback/demo context remain under the static root, while controlled production observations are read from `data/processed/macro/observations.json`.
- Articles/news/evidence that are explicitly labelled demo remain illustrative and are not treated as canonical facts.

Do not move or rename `data/mock/` during Phase 4.4F; path cleanup is deferred until the production contracts are stable.

## Implementation Step 3 — Market Module

Implemented Market views: Overview, Projects, Supply & Sales, Pricing, Developers and News. The module uses structured mock JSON plus shared Resolver, FilterEngine and ChartTools utilities. Project details open in the shared drawer and can be deep-linked with `?project=<id>`. All Market figures in this build are illustrative demo data.


## Implementation Step 4

Legal module added with structured illustrative mock data:

- Overview, Documents, Effective Soon, Topics and News views
- Agency/topic/status/scope filters with URL state
- Legal document deep links and detail drawer
- Document lifecycle and upcoming effective-date derivation
- Related-document relationships including reverse relation display
- Clear separation between official document records and analysis/news evidence

All legal records in Step 4 are illustrative demo data and must not be treated as authoritative legal information.


## Implementation Step 5 — Infrastructure Module

Implemented Infrastructure views: Overview, Projects, Regions, Timeline and News.

- Structured infrastructure project master records
- Schedule history with current/superseded targets
- Milestone/event timeline kept separate from schedule records
- Progress display only when a numeric mock value exists
- Region/type/status/completion filtering with URL state
- Infrastructure project deep links via `?project=<id>`
- Cross-links from Infrastructure to related real-estate projects
- Market project drawer now surfaces related infrastructure where available
- Infrastructure news remains an evidence layer separate from project status and schedule history

Project names may reference real-world infrastructure assets, but all progress percentages, investment figures, dates, status labels and schedule records in Step 5 are illustrative mock data only.

## Implementation Step 6 — Macro Module

Implemented Macro views: Overview, Rates, FX, Gold, Liquidity, Inflation and News.

- Structured indicator master records separated from historical observations
- Current / previous / change derived from observations rather than hard-coded into the page
- Daily, monthly and event-driven frequencies supported
- Policy-rate event series rendered as a stepped chart
- 1M / 3M / 1Y / All chart ranges
- Data period kept separate from publication date
- Macro indicator deep links via `?indicator=<id>` and reusable detail drawer
- Macro articles remain an evidence layer linked by `indicator_ids`
- Credit, money supply and interbank series are kept separate instead of forcing incompatible units onto a single chart

All Macro values in Step 6 are illustrative mock data only and are not live market information.


## Implementation Step 7 — Global Search & Frontend Integration

Global header search is now connected to the structured demo datasets across all five pages.

- Searches Projects, Developers, Legal Documents, Infrastructure Projects, Macro Indicators, Events and Articles/Research
- Vietnamese search is accent-insensitive (`Đồng Nai` and `dong nai` match the same records)
- Exact entity/title/ID/alias matches rank above articles that only mention the term
- Supports project/developer aliases such as `NLG`, legal document numbers and indicator IDs
- Search results deep-link into the relevant module/drawer or filtered evidence view
- Search is loaded lazily and uses the shared DataStore cache; no AI, backend or database is required
- Keyboard shortcut `Ctrl/Cmd + K`, arrow-key navigation and Enter-to-open are supported

This completed the original frontend implementation layer. Subsequent Phase 4 work added source registries, curated real datasets, collectors, controlled production promotion and repository persistence. Historical v7 demo fixtures are retained only as explicitly labelled fallback/context data.

## Phase 4.4F — Production Hardening Baseline

Phase 4.4F locks the accepted Phase 4.4E/4.4E.2 production behavior before broader automation is added.

- Daily USD/VND central rate and SJC buy/sell observations use the narrow two-source corroborated auto-persistence gate.
- Re-running the same production facts is idempotent: no duplicate logical key is appended and the last good repository state is retained.
- `data/state/update-status.json` is a repository snapshot; scheduled freshness checks rebuild a runtime snapshot from current data.
- GitHub Actions are pinned to Ubuntu 24.04 and Node.js-24-compatible official action majors to avoid runner/runtime migration surprises.
- The legacy `data/mock/` path is kept for compatibility, while metadata and documentation explicitly distinguish demo, curated and controlled-production data.

See `docs/PHASE4_4F_PRODUCTION_HARDENING.md` for the baseline contract and deferred items.

## v7.1.0 — Source Registry & Provenance Foundation

v7.1.0 starts directly from the stable v7.0.0 Golden Baseline. It does not change the page structure, routing, search, filters, charts, mock business values or localization.

Added in this release:

- `data/mock/core/sources.json` with 13 source definitions resolving every source ID already used by the v7 demo records
- `assets/js/provenance.js`, an isolated provenance layer with safe fallback behavior
- Footer **Data Sources** registry on all five pages
- Clickable source references in Market, Legal, Infrastructure and Macro detail/data views
- Source context can show source/data date, observation period, publication date, collection method, update frequency and methodology note when the underlying record provides them
- Record-level original URLs are supported; the illustrative registry intentionally does not invent live URLs
- Source Registry failure does not block the v7 page runtime; source IDs remain available as fallback labels

Source priority is a sourcing preference, not a score. The demo convention is P1 for primary official sources, followed by first-party issuer/operator sources, research sources and media evidence.

All existing v7 mock datasets remain regression fixtures and are unchanged. The only new mock dataset is the Source Registry itself.


## v7.1.1 — Units & Display Standards

v7.1.1 starts directly from the accepted v7.1.0 Source/Provenance release and only changes presentation formatting. No localization, collector, routing, search, filter or page-structure changes are included.

Added in this release:

- `assets/js/formatters.js` as the shared presentation-only formatting layer
- `config/display-standards.json` documenting Vietnam-first display conventions
- Real-estate ASP displayed as `mn VND/m²` while canonical values remain raw VND/m²
- Large VND infrastructure investment displayed as `VND bn` or `VND tn` without altering source values
- Domestic gold displayed as `mn VND/tael`; FX as `VND/USD`; annual rates as `% p.a.`
- Market, Infrastructure, Macro and shared charts use the same formatter definitions
- Home demo indicator display strings are aligned to the same conventions; their underlying illustrative values are unchanged

Display conversion is never written back to canonical datasets. Missing values remain `null` / `—` and are never converted to zero. International benchmark series retain their natural source unit such as `USD/oz`.

## v7.2.0 — Static VI/EN Localization

v7.2.0 starts directly from the accepted v7.1.1 baseline and adds only an optional localization overlay for static/common interface text.

- Default UI language is Vietnamese; users can switch `VI · EN` in the header.
- Language preference is stored locally in the browser when available.
- Shared navigation, search shell, footer, page titles/descriptions, demo notices and page tabs are translated.
- Dynamic records, project names, legal document titles, article titles, source names, tables/cards generated by page modules and business data remain unchanged in this stage.
- All v7.1.1 page/runtime modules remain unchanged. Localization is loaded last and is not a dependency of DataStore, search, filters, charts or page boot.
- If the localization overlay fails or is removed, the stable English v7.1.1 interface continues to operate.

Dynamic component labels will be considered separately in v7.2.1 after v7.2.0 is reviewed.

## v7.2.1 — Dynamic UI Labels

v7.2.1 starts directly from the accepted v7.2.0 static-localization release. It keeps all v7.2.0/v7.1.1 page modules and business data unchanged and adds one optional DOM-localization overlay loaded last.

Added in this release:

- Vietnamese translation for dynamic filter labels/options, status badges, table headings, drawer section labels, empty/error states, global-search result groups and Source Registry detail labels
- Dynamic count/date helper phrases such as `8 projects`, `In 30 days`, and `Demo data · <date>`
- Market / Legal / Infrastructure / Macro dynamic interface terminology while preserving project names, legal-document titles, article titles/summaries and source names in their original language
- VI/EN switching also updates newly rendered dynamic UI through a `MutationObserver` overlay
- Dynamic localization remains non-fatal and is never called by DataStore, Search, Resolver, FilterEngine, ChartTools or page-domain modules

Chart canvas legends/series labels and source-authored content are intentionally not rewritten in this release.


## Phase 4.5 — Macro Automation Complete

Phase 4.5 now covers four controlled automatic groups: daily FX/gold, official monthly NSO statistics, corroborated customer deposit/lending ranges, and corroborated SBV administered policy-rate events. Each group has its own narrow production and persistence gate; unrelated indicators cannot leak into an automatic run.

Customer rates require a complete four-component monthly range bundle corroborated by VNBA and VietnamPlus/VNA. Policy rates require a complete three-rate event corroborated by VietnamPlus/VNA and Thoi Bao Ngan Hang. Partial bundles retain the last good repository state.

Operational QA runs with the daily freshness check, and `.github/workflows/phase45-validation.yml` provides a single manual validation action for Phase 4.5A–4.5D.

See `docs/PHASE4_5_COMPLETE_MACRO_AUTOMATION.md` for the consolidated contract.


## Phase 4.6 + 4.7 — Registry Watch & Market Coverage

Legal and Infrastructure now have a read-only weekly assisted source-watch workflow. It fingerprints canonical source pages, discovers keyword-matched official links and produces a human review queue; it never writes canonical registry or frontend data automatically. Infrastructure schedule revisions remain append/supersede history rather than overwrite.

Market coverage expands to 12 curated projects and 9 developers with first-party project sourcing. The additional projects are Vinhomes Grand Park, The 9 Stellars, Celesta Gold and Essensia Parkway. Quantitative observations remain separate from project masters: missing ASP, sales, supply or absorption stays blank.

See `docs/PHASE4_6_7_REGISTRY_MARKET.md`.


## Phase 4.8 + 4.9 — Historical Series & Change Intelligence

Historical analysis now derives from the existing canonical records rather than a second history database. Macro uses append-only production observations; Legal uses issued/effective dates and amendment relations; Infrastructure uses current/superseded schedules plus milestones; Market uses dated project and comparable research observations.

A shared `HistoryEngine` powers prior-observation deltas and Home “What Changed” cards. Missing history is never fabricated: one-point series remain one-point series until sourced observations are available, and incompatible Market sources are not mechanically combined.

See `docs/PHASE4_8_9_HISTORY_INTELLIGENCE.md`.
