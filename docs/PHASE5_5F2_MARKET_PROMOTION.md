# Phase 5.5F2 — Market Candidate Preview → Promote

## Goal
Add an explicit review gate between live market-source candidates and production datasets.

## Inputs
Staged candidate files:
- `data/candidate/market/observations.json`
- `data/candidate/market/articles.json`

The current staging set comes directly from the successful 5.5F1 live artifact:
- CBRE HCMC Landed Q2/2026: new supply 1,934
- Nam Long official update dated 02/10/2026
- Nam Long Experience update dated 21/09/2026

## Preview
`scripts/market_candidate_promotion.py --mode preview`

For market observations, logical identity is:
- scope type
- region IDs
- segment IDs
- period
- source ID

For articles, logical identity is:
- source URL
- source ID

Each candidate is classified:
- `new`
- `unchanged`
- `conflict`

A conflict means an existing logical record has materially different content. Promotion is refused.

## Promote
`scripts/market_candidate_promotion.py --mode promote`

Promotion is append-only:
- new market observations append to `data/mock/market/observations.json`
- new articles append to `data/mock/articles/articles.json`
- unchanged rows are not duplicated
- any conflict blocks the full promotion

Workflow: **Market Candidate Preview Promote**

The workflow defaults to Preview. Promote must be explicitly selected.

## Current expected preview
- 1 observation candidate → new
- 2 article candidates → new
- 0 conflicts

## Web impact after promotion
Once promoted:
- HCMC · Landed · Q2/2026 becomes available in Supply & Sales when the landed segment is selected
- new Nam Long official updates become available in Market News & Research
- Waterpoint, Mizuki Park, Izumi City and Akari City receive more recent project-linked official activity
- Listing Market asking-price history remains unchanged

Developer-stated facts stay labelled as developer evidence and are not converted into independent market benchmarks.
