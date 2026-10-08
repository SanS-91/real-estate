# Phase 5.5A — Listing Market Intelligence Pilot

## Goal
Add a separate secondary-market/listing layer to Market Research without mixing asking prices with official project sales, executed transaction prices, CBRE/Savills benchmarks or absorption.

## Pilot
The Global City is the first project pilot using Batdongsan.com.vn.

The pilot stores:
- apartment asking-price range
- 1-year portal price trend
- popular area range
- 1BR / 2BR / 3BR asking-price ranges
- ancillary portal activity metrics such as listing count and 7-day views
- nearby map-label asking-price snapshot for research comparables

## Data separation
Listing data is stored in:
- `data/mock/market/listing-observations.json`
- `data/mock/market/listing-comparables.json`

It is intentionally **not** stored in `market/observations.json`.

## Semantics
- asking/listing price != executed transaction price
- listing count != project inventory
- portal views != demand or absorption
- map labels != appraisal comparables
- volatile listing counts/views are ancillary only and are excluded from primary KPIs

## UI
Research shows a Listing Market layer inside the Market-first section.
Market Project drawer shows the same layer separately from canonical ASP and absorption.

## Next expansion
After validating the pilot, Phase 5.5B can map listing sources to the remaining curated projects and build append-only snapshots for historical asking-price/listing trends.
