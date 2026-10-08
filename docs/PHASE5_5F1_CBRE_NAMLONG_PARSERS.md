# Phase 5.5F1 — CBRE + Nam Long Live Parsers

## Goal
Move the Phase 5.5F source probes into structured candidate extraction for two priority sources while retaining review-before-production.

## CBRE
Source:
- HCMC Q2/2026 Figures, Vietnamese official page.

Structured candidate fields:
- region: HCMC
- segment: apartment / landed
- period: 2026-Q2
- new supply

Current production already contains the CBRE apartment Q2 figure (850 units). The parser therefore treats that observation as unchanged when the live source agrees.

The landed Q2 figure (1,934 newly launched products) is not currently present in production and becomes a candidate for review.

No sales / absorption / ASP fields are inferred when the public source does not provide a directly comparable value.

## Nam Long official
Two initial live article targets:
- 02/10/2026 JV / township update
- 21/09/2026 Nam Long Experience update

The parser extracts:
- article date/title
- referenced project IDs
- update tags such as launch / sales / handover
- explicitly stated structured facts such as developer-reported 100% absorption or certificate progress

These records remain developer evidence/articles. They do not become independent market benchmark observations.

## Candidate outputs
- `data/candidate/market/observations.json`
- `data/candidate/market/articles.json`
- `data/candidate/market/market-source-candidate-report.json`

The collector compares live extraction with existing production and emits only new/materially changed candidates.

## Safety
- production is never written by the collector
- no metric inference from missing fields
- CBRE market research remains separate from listing asking history
- Nam Long developer claims remain labelled as developer evidence
- live parser failure creates a diagnostic report, not a production mutation
- fixture tests cover parsers without network dependency

## Web impact
No web-visible change occurs until candidate records are reviewed and explicitly promoted.
