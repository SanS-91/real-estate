# Phase 5.5B.1 — Market Surface Integration

## Goal
Make the new listing-market data visible directly in the Market module instead of hiding it only inside project drawers and Research.

## Changes
- Key Projects / Projects table adds Verified ASP, Asking range and 1Y listing trend as separate columns.
- Pricing Snapshot adds a Verified price / Listing market toggle.
- Listing-market charts render low/high asking-price ranges by project; no midpoint or synthetic price is created.
- Pricing view uses the same toggle and displays either verified source observations or listing snapshots.
- Listing Market is the default price layer because it currently has broader project coverage.

## Semantics
- Verified ASP remains separate from listing asking prices.
- Listing asking range is not a transaction price.
- 1Y portal trend is a portal-derived listing-market indicator.
- Partial projects remain blank where aggregate price is unavailable.

## Next
Phase 5.5C: assisted refresh + append-only historical listing snapshots and change detection.
