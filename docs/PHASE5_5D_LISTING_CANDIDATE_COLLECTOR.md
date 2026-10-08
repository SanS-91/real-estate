# Phase 5.5D — Listing Market Candidate Collector

## Goal
Reduce manual refresh work without allowing unreviewed portal data to write directly into production history.

## Collector
`scripts/listing_candidate_collector.py` reads only the Batdongsan.com.vn URLs already mapped in the latest production listing snapshot.

It extracts, when explicitly present in page text:
- asking-price low/high per m²
- 1-year portal price trend
- popular area low/high
- listing count
- 7-day project views

## Candidate policy
Only changes to primary listing fields create a candidate:
- asking range
- 1-year trend
- popular area

Listing count and 7-day views are volatile ancillary fields. Their change alone does not create a new candidate snapshot.

If an existing full-coverage project suddenly yields no aggregate asking range, the source is treated as degraded and no candidate is produced.

## Workflow
**Listing Market Candidate Collector** is manual in Phase 5.5D.

By default it:
1. collects all mapped pages, or one supplied project
2. writes candidate + collector report in the runner
3. validates the candidate through the Phase 5.5C append-only preview
4. uploads the outputs as a 14-day Actions artifact

`persist_candidate` defaults to false. Turning it on commits only candidate staging files, never production.

Production promotion remains a separate explicit action through **Listing Market Assisted Refresh → Promote**.

## Safety
- no browser automation or protection bypass
- no URL discovery outside the curated mapping
- no direct production write from the collector
- no inferred values when fields are absent
- no candidate created solely because listing count/views changed


## Live smoke result — 2026-10-08
A GitHub-hosted Ubuntu 24.04 runner received HTTP 403 for all 12 mapped Batdongsan.com.vn project URLs. The collector therefore records `source_access: blocked` and produces no candidate rows.

This is treated as a source-access limitation, not as "no market change". The project will not add bypass/proxy techniques to evade the source's access controls. Batdongsan.com.vn remains a manually curated / browser-accessible secondary source until an approved access path or licensed data service is available.
