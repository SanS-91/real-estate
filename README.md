# Vietnam Real Estate Market Intelligence

Implementation v1 is being built sequentially as a static-first research webapp for GitHub Pages.

## Current implementation status

- Step 1 — Repository skeleton, shared shell and responsive design system: complete.
- Step 2 — Home dashboard skeleton and shared content components: complete.
- Step 3 — Market module: complete.
- Step 4 — Legal module: complete.
- Step 5 — Infrastructure module: complete.
- Step 6 — Macro module: complete.
- Step 7 — Global structured search and final frontend integration: complete.
- All current values, dates and developments are illustrative mock data only.

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

`config/settings.json` currently points to:

```text
./data/mock/
```

Later implementation steps will switch the same frontend interface to structured processed data without changing the page layout.

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

This completes the frontend implementation layer. All current datasets remain illustrative mock data. The next phase is source registry + collectors for real data ingestion.

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
