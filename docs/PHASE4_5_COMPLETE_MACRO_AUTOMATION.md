# Phase 4.5 — Macro Automation Complete

Phase 4.5 consolidates four safe automatic Macro paths while preserving append-only repository history and retain-last-good failure behavior.

## 4.5A — Official monthly statistics
- CPI YoY, CPI MoM, Core CPI YoY, Credit Growth YTD, Bank Funding Growth YTD.
- Official NSO only, verified canonical facts.
- Watch window: 10:45 ICT on days 1–10 each month.

## 4.5B — Customer deposit/lending ranges
- Four range components only: deposit 6–12M low/high and lending average low/high.
- Requires the complete four-component bundle for one common month.
- Every component must be corroborated by VNBA + VietnamPlus/VNA.
- Weekly watch: Tuesday 11:15 ICT.
- Priority short-term lending remains evidence-only.

## 4.5C — SBV administered policy rates
- Refinancing, rediscount, and overnight lending rates only.
- Requires a complete three-rate event on one effective date.
- Requires VietnamPlus/VNA + Thoi Bao Ngan Hang corroboration.
- Weekly watch: Thursday 11:30 ICT.
- Interbank overnight remains outside automatic production.

## 4.5D — Operational QA
- Daily freshness workflow now runs a structural Phase 4.5 safety QA.
- Checks canonical record count, duplicate IDs/logical keys, baseline coverage and safe repository-only publish flags.
- A dedicated `Phase 4.5 Macro Automation Validation` workflow provides one-click regression validation for 4.5A–4.5D.

## Safety contract
- Existing logical keys are immutable.
- No record drops.
- Stale repository baselines are blocked.
- Auto paths never write directly to frontend files.
- Source failure or insufficient corroboration retains last good repository data.
- No partial customer-rate or policy-rate bundles are auto-published.
