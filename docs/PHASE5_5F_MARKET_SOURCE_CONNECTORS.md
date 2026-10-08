# Phase 5.5F — Automated Market Source Connectors

## Goal
Increase source diversity without mixing source roles or writing unreviewed research directly to production.

## Initial targets
- CBRE Vietnam
- Savills Vietnam
- JLL Vietnam
- Cushman & Wakefield Vietnam
- Nam Long official news / project updates

## Connector behavior
The first 5.5F connector is deliberately conservative. It only:
1. reads configured source URLs
2. classifies access as reachable / blocked / http-error / fetch-error
3. captures basic page metadata such as title, description and date mentions
4. writes a candidate-side connector report artifact

It does not parse or promote market KPIs yet.

## Why this staging step exists
Before adding source-specific parsers, GitHub-hosted runner access must be tested. A source that is blocked or unstable should not become an automated production dependency.

## Data separation
- listing portals remain in listing-asking history
- developer official sources remain project / launch / pricing / sales-update evidence
- consultancy sources remain market benchmark / market-report evidence

No connector may write consultancy metrics into listing-price history.

## Automation
Workflow: **Market Source Connector Probe**

Runs:
- manually
- scheduled twice weekly

The workflow uploads its report as an artifact and does not commit production data.

## Next gate
Only sources proven reachable and stable will receive source-specific KPI parsers. Parsed results will still go to candidate / review before promotion.
