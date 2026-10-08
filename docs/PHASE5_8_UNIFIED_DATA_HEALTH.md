# Phase 5.8 — Unified Automation & Data Health

## Goal
Close Master Phase 5 by giving Market, Legal, Infrastructure and Macro one operational health layer.

## What is combined
For each tracked dataset, the health layer records:
- production freshness
- latest workflow state
- latest successful workflow run
- source/access mode
- candidate persistence mode
- candidate backlog / conflicts when measurable
- failure behavior
- last production timestamp

## Source/access semantics
- automated: source is handled through scheduled collectors
- automated-candidate: collector creates reviewed candidates before promotion
- automated-candidate-review: same, with an explicit human review requirement
- assisted-browser: source is not reliably accessible from GitHub-hosted runners and approved browser-assisted capture is used instead
- automated-plus-curated: automation supports the dataset, but curated registry work remains valid

An assisted source is not treated as a system failure simply because direct GitHub-hosted access is unavailable.

## Workflow health
The Unified Data Health workflow reads GitHub Actions run history for the configured collectors.

This lets the website distinguish:
- production still fresh because last-good data was retained
- collector currently failed/degraded
- workflow currently running
- source requires review
- candidate backlog exists

## Candidate backlog
Backlog counts are source-aware:
- Market benchmark candidates are compared with production so already-promoted identical rows do not remain falsely counted as backlog.
- Legal and Infrastructure candidates are counted from persisted review staging when present.
- Macro candidate evidence remains artifact-oriented; health reports that candidate mode rather than inventing a persisted backlog.

## Web surfaces
### Home
A compact four-card Data Health block shows:
- Market
- Legal
- Infrastructure
- Macro

Each card shows module status, tracked dataset count and candidate backlog.

### Data Status
The maintenance dashboard adds Module Operations:
- workflow health
- source/access mode
- candidate backlog
- last successful run

The existing dataset freshness table remains available below it.

## Automation
Workflow: **Unified Data Health**

Schedule:
- 08:05 ICT daily, after the existing 07:45 freshness check
- also runs on relevant production/candidate/config changes

The workflow writes:
`data/state/data-health.json`

It may commit only this health snapshot. It never promotes candidates or changes canonical domain data.

## Master roadmap consequence
With Phase 5.8 complete:
- Master Phase 4 — Source Registry & Auto Data Collection: COMPLETE
- Master Phase 5 — Automation: COMPLETE

The next work package is:
**6.0 — Cross-module Intelligence Model**
