# Phase 6.3 — Historical Coverage Expansion

## Goal
Increase time-series depth with sourced history and make historical gaps measurable.

Phase 6.3 does not synthesize missing periods. It separates:
- real historical backfill,
- future snapshot accumulation,
- coverage diagnostics.

## Current audit before backfill

### Listing Market
- 12 tracked projects
- each currently has one production snapshot dated 2026-10-08
- zero project series are trend-ready under the minimum three-snapshot rule

Batdongsan.com.vn remains assisted-browser because GitHub-hosted access is blocked. Historical snapshots are not reconstructed from volatile portal fields.

### Market Research
Before 6.3:
- CBRE HCMC apartment: 2025-Q4, 2026-Q1, 2026-Q2
- CBRE HCMC landed: 2026-Q2 only
- C&W HCMC apartment: 2026-Q2
- C&W HCMC landed: 2026-Q2
- Savills annual 2025 benchmarks remain separate annual benchmark series

### Legal
Canonical Legal records already span 2023–2026. Legal history is based on issued/effective dates and amendment/implementation relationships rather than artificial periodic snapshots.

### Infrastructure
Canonical schedules already preserve superseded/current changes. Several projects have two schedule records; others still have one milestone only.

## Reviewed Market backfill

The reviewed backfill adds five source-specific observations.

CBRE:
- HCMC apartment Q3/2025 — 2,549 new launches
- HCMC landed Q3/2025 — 220 new launches
- HCMC landed Q4/2025 — 4,569 new launches
- HCMC landed Q1/2026 — 87 new launches

Cushman & Wakefield:
- core HCMC apartment Q1/2026 — approximately 1,200 new launches
- absorption approximately 25%

Sources:
- CBRE HCMC Figures Q3 2025
- CBRE HCMC Figures Q4 2025
- CBRE HCMC Figures Q1 2026
- Cushman & Wakefield HCMC apartment Q1 2026 research update

Approximation qualifiers are retained. Source geography wording such as former/core HCMC is kept in methodology notes.

After promotion, CBRE apartment and landed each have a four-quarter series from 2025-Q3 through 2026-Q2.

## Historical coverage audit

`scripts/build_history_coverage.py` builds:

`data/state/history-coverage.json`

Rules are controlled by:

`config/history-coverage.json`

Current readiness thresholds:
- Listing Market: 3 snapshots
- quarterly Market Research: 4 distinct periods per source-specific series
- Legal: at least 3 issued/effective years at module level
- Infrastructure: at least 2 schedule records per project series

These are coverage diagnostics, not investment scores.

## Backfill staging

`scripts/market_historical_backfill.py` reads the reviewed backfill config and:
- validates source IDs and numeric bounds
- deduplicates against production using the same logical series key
- stages only new records in Market candidate files
- refuses conflicts
- never writes production

The existing Market Preview → Promote gate remains authoritative for production mutation.

## Listing history path

Listing history must grow prospectively:
- assisted capture when the portal is reviewed
- append snapshot only after review
- no reconstruction of old asking prices from current portal pages
- primary trend readiness begins at three real snapshots

## Master Phase 6 exit

6.0 established the shared cross-module intelligence model.
6.1 deepened Project intelligence.
6.2 added Region and Developer intelligence.
6.3 adds measurable historical depth and real research backfill.

After the reviewed backfill is promoted and coverage diagnostics pass, Master Phase 6 can be marked complete.
