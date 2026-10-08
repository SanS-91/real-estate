# Phase 5.5F3 — Expanded Automated Research Sources

## Goal
Extend automated research coverage beyond CBRE and Nam Long while preserving source semantics and review-before-production.

## Sources
- Cushman & Wakefield Vietnam — HCMC Residential MarketBeat Q2/2026
- JLL — HCMC Residential Market Dynamics Q2/2026
- Savills Vietnam — Viet Nam Real Estate Market Brief Q2/2026

## Parsing policy
### Cushman & Wakefield
Numeric market metrics may become structured candidates only when they are explicitly present on the public page.

Important precision rule:
- "over 1,300 apartment units" is **not** stored as exact new supply = 1,300.
- apartment absorption 31% may be captured as source-published.
- landed supply around 1,700 units, absorption around 36%, and nearly 870 units may be staged with methodology explicitly retaining the source's approximate nature.

These are candidate observations only and still require Preview → Promote review.

### JLL
The current public Q2/2026 page exposes qualitative takeaways but no sufficiently comparable public numeric series for this pipeline.
Therefore JLL is collected as **research evidence/article candidate**, not forced into a benchmark metric.

### Savills
The Q2/2026 market brief is collected as **research evidence/article candidate**.
Existing Savills 2025 numeric benchmark remains separate and is not overwritten.

## Candidate flow
All enabled F3 targets run through:
Live source → parser → candidate → Preview → Promote

No F3 parser writes production directly.

## Web impact
This phase itself does not change the website until candidates are promoted.
Research articles will appear in Market News & Research after promotion.
Numeric market observations, if approved, remain distinct from Listing Market asking-price history.
