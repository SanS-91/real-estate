# Phase 5.5C — Assisted Refresh & Listing History

## Operating model
Listing-market history is append-only. A snapshot is keyed by project, asset type, source and observation date.

The staging file is:
`data/candidate/market/listing-observations.json`

The production history remains:
`data/mock/market/listing-observations.json`

## Workflow
**Listing Market Assisted Refresh** has two explicit modes:
- Preview: validate and classify candidate rows only.
- Promote: append new logical snapshots if there are no conflicts, then commit production history.

An existing logical key with different data is a conflict and is never silently overwritten.

## Change classification
- new: first snapshot in a series
- new-unchanged: new date, tracked values unchanged
- new-changed: new date, at least one tracked value changed
- unchanged: same logical key and same values
- conflict: same logical key but different values

## Web
Project drawers now include Listing Price History. The chart reads all real snapshots for that project. With the current dataset it intentionally starts with one real point dated 2026-10-08; future approved snapshots extend the chart automatically.

## Next
A later collector phase can populate the candidate file automatically. Promotion remains gated until source extraction quality is proven.
