# Phase 4.8 + 4.9 — Historical Series & Change Intelligence

## Design
The existing canonical records remain the source of truth. Phase 4.8 does **not** create a second history database and does not fabricate missing historical points.

A shared browser-side `HistoryEngine` normalizes the dated history already present in each module:

- **Macro:** append-only production observations by indicator.
- **Legal:** issued/effective dates plus document amendment/supplement relations.
- **Infrastructure:** schedule records with current/superseded status plus dated milestones.
- **Market:** dated project observations/phases and comparable research series.

## Phase 4.8 — Historical series
- Macro charts and delta calculations use the shared series ordering.
- Legal document drawers show lifecycle history including amendments/supplements.
- Infrastructure drawers combine schedule revisions and milestones while preserving superseded targets.
- Market project drawers show dated source-backed project history.
- No synthetic backfill is added. A one-point series remains a one-point series until a sourced historical or future observation exists.

## Phase 4.9 — What Changed intelligence
The Home dashboard derives change cards from canonical history:
- FX / gold change versus the prior stored production observation.
- Infrastructure milestone or schedule revision.
- Comparable HCMC apartment new-supply change using the same CBRE series.
- Legal amendment/supplement relationships.

The 7-day recap remains live-derived from current production and curated events, so it does not require a manually maintained weekly snapshot.

## Safety
- no canonical history overwrite
- no cross-source arithmetic for incomparable market definitions
- no inferred missing ASP / sales / absorption
- no synthetic legal or infrastructure dates
- static Home JSON remains fallback only
