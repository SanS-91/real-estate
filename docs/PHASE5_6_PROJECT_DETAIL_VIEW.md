# Phase 5.6 — Project Detail View

## Goal
Keep the right-side drawer as a fast project quick view while adding a full project intelligence view for deeper review.

## Route
`market.html?view=project-detail&id=<project-id>`

The drawer now includes **Xem chi tiết dự án** linking to this route.

## Sections
- project header and key metrics
- overview / developer / location / segment context
- listing asking-price history with chart + snapshot table
- verified project pricing & sales evidence
- official / research updates with source links
- legal research shortcuts
- related infrastructure
- phase structure
- consolidated data provenance

## Data principles
- uses existing curated project relationships
- listing-market data remains separate from verified project data
- source links remain clickable
- legal-topic links are research shortcuts, not legal applicability conclusions
- missing values remain blank / unavailable rather than estimated

## Drawer behavior
The existing project drawer remains the quick view. The full project page is additive and does not replace drawer interactions elsewhere in Market.
