# Phase 5.5E — Source Diversification + Assisted Listing Refresh

## Goal

Increase market-data coverage without relying on unstable scraping and without weakening the Phase 5.5C review gate.

Phase 5.5E separates sources by role:

- listing portals → listing asking market
- developer official sources → official project / launch / pricing / sales updates
- consultancy research → market benchmark / supply / sales / absorption / outlook

These layers must not be mixed as if they were equivalent observations.

## Source registry

`config/market-source-registry.json` is the canonical registry for source provenance and supported data layers.

Batdongsan.com.vn is currently:

- role: listing portal
- access: assisted browser
- GitHub-hosted automation status: blocked
- supported layer: listing-asking

The project does not add proxy/bypass behavior for blocked access controls.

Developer official sources and CBRE / Savills / JLL / Cushman & Wakefield are registered as diversification targets. Automation is permitted only when the source is accessible and stable.

## Assisted listing capture

Workflow: **Listing Market Assisted Capture**

Use it after reviewing an existing mapped Batdongsan project page in a normal browser.

Inputs:

- project_id
- exact source URL
- source data date/period
- asking price low/high (VND mn/m2), when available
- 1Y trend %, when available
- popular area low/high, when available
- listing count and 7-day views as ancillary metrics only

The workflow:

1. builds exactly one candidate snapshot
2. attaches provenance metadata
3. validates the source through the registry
4. runs the existing append-only history Preview
5. uploads the candidate/report artifact
6. optionally persists candidate staging only

It does **not** write production.

After review, use **Listing Market Assisted Refresh → Promote** to append an approved snapshot.

## Safety and data semantics

- no direct production write from capture
- no bypass of blocked access controls
- no unknown project IDs
- no unregistered listing source
- no mixing consultancy benchmark data into listing asking history
- price low/high must be both supplied or both blank
- area low/high must be both supplied or both blank
- listing count/views remain ancillary
- production remains append-only and conflict-protected

## Web impact

This infrastructure change alone does not create a new history point.

The website changes only after an approved candidate is promoted into `data/mock/market/listing-observations.json`.

Until then:

- mapped/project coverage stays unchanged
- priced coverage stays unchanged
- each project keeps its existing history snapshot count
