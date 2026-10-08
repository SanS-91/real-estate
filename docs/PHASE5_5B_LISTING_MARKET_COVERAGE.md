# Phase 5.5B — Listing Market Coverage Expansion

## Coverage
All 12 curated Market projects now have a Batdongsan.com.vn page mapping.

- 8 projects have a full aggregate asking-price snapshot.
- 4 projects have partial snapshots only: Izumi City, The 9 Stellars, Celesta Gold and Essensia Parkway.
- Partial snapshots keep missing aggregate price fields blank.

## Semantics
- full = portal publishes a comparable aggregate asking-price range for the mapped product type
- partial = page mapping or other source-backed portal fields exist, but no defensible aggregate asking-price range is promoted
- listing counts and 7-day views remain ancillary, volatile fields and are excluded from primary KPIs
- listing data remains separate from canonical Market observations

## History
The listing dataset is append-only by logical snapshot ID. Future refreshes should add a new dated record rather than overwrite historical snapshots.

## Next
Phase 5.5C can automate assisted snapshot refresh, change detection and historical asking-price charts while keeping human review before promotion.
