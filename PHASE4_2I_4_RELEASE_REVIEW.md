# Phase 4.2I.4 — Banking Frontend Sync

## Scope
- Promote the already-persisted `credit-growth-ytd` and `bank-funding-growth-ytd` records into the existing controlled Macro frontend gate.
- Keep values data-driven from `data/processed/macro/observations.json`; no frontend value snapshot is hard-coded.
- Add Bank Funding Growth YTD to the Liquidity view and Macro Overview Key Indicators.
- Keep production and demo history mutually exclusive per indicator.
- Surface one-observation coverage as `Latest only` and explicitly state that no synthetic history is created.
- Update the controlled-data banner to acknowledge verified NSO banking indicators.

## Production records used
- `credit-growth-ytd` — 10.89% — 2026-09 — NSO Vietnam — verified / Canonical.
- `bank-funding-growth-ytd` — 9.78% — 2026-09 — NSO Vietnam — verified / Canonical.

## Safety
- Existing repository-publish checks remain unchanged.
- Existing unit/source/evidence/final-status gate is extended only to the two approved banking indicators.
- Demo observations for an indicator are removed once any approved production observation exists.
- No collector, production policy, workflow, persistence script, or processed data file is modified.
- Frontend does not fabricate previous periods, deltas, or trend history when only one production observation exists.
