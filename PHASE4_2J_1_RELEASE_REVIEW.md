# Phase 4.2J.1 — SBV Customer Rates Discovery & Policy

## Goal
Open the official-source path for customer interest rates without forcing the existing demo scalars into production.

## Key methodology decision
SBV's monthly customer-rate bulletin reports **ranges**, not a single scalar `12M Deposit Rate` or a single scalar `Average Lending Rate`.

Therefore Phase 4.2J.1 intentionally does **not** map official observations onto the existing demo indicators:
- `deposit-rate-12m-average`
- `lending-rate-average`

Instead the candidate layer adds five source-faithful indicators:
- `deposit-rate-vnd-6-12m-low`
- `deposit-rate-vnd-6-12m-high`
- `lending-rate-vnd-average-low`
- `lending-rate-vnd-average-high`
- `priority-short-term-lending-rate-vnd`

This preserves methodology and prevents a range endpoint from being mislabeled as an average.

## Source architecture
- Preferred source: State Bank of Vietnam (`sbv-vietnam`)
- Schedule: monthly release
- Evidence status from direct SBV bulletin: `verified`
- Candidate source key: `sbv-customer-rates`
- Source pool: `customer-rates`

The collector supports the SBV publication shape where a press-release/detail page links to an attached PDF. The generic fetch layer now extracts text from PDFs before parsing.

## Safety gates
- Candidate only in this phase.
- No new rate indicator is added to `production_promotion_policy.json`.
- No frontend mapping is activated; range components are explicitly marked `range-component-not-published`.
- Existing 8 production records are untouched.

## Expected next step
After the live SBV collector succeeds, Phase 4.2J.2 will review the candidate artifact and decide the frontend composition/promotion contract for range display.
