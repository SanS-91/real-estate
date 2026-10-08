# Phase 5.5F4 — Multi-source Supply & Sales UI

## Goal
Allow multiple market-research sources to coexist for the same region / segment / period without blending them into one implied canonical series.

## UI behavior
Supply & Sales now has a dedicated **Source** selector.

The chart and Selected Source History show only the chosen source.

A separate **Source Comparison** table shows every available source for the selected region / segment side-by-side.

Important interpretation rules:
- values from different research houses are not averaged
- source methodologies may differ
- blank fields stay blank
- the selected source is highlighted in the comparison table
- CBRE is preferred as the default source when present to preserve the existing overview behavior

The source selection is stored in the `source` query-string parameter.

## Why this is required
Phase 5.5F3 produced valid C&W Q2/2026 market candidates while CBRE already has Q2/2026 observations. Without source-aware UI, both could appear as duplicate/conflicting rows with no clear interpretation.

F4 makes that distinction explicit before any C&W numeric candidate is promoted.

## Next gate
After this UI is deployed and validated, C&W numeric candidates can be Previewed and promoted:
- HCMC Landed Q2/2026
- HCMC Apartment Q2/2026

The numeric records remain source-specific and never replace CBRE observations.
