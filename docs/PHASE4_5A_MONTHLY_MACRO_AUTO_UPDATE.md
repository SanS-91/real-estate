# Phase 4.5A — Monthly Macro Auto-Update

## Scope

Phase 4.5A adds a narrow automatic repository path for five official monthly NSO facts:

- `cpi-yoy`
- `cpi-mom`
- `core-cpi-yoy`
- `credit-growth-ytd`
- `bank-funding-growth-ytd`

It does not broaden customer-rate, policy-rate, interbank, FX or gold automation.

## Schedule

The existing `Macro Candidate Collector` workflow now has a third scheduled trigger:

- `03:45 UTC` / `10:45 ICT`, days `1–10` of each month.

This release window is intentionally separate from the existing daily FX/gold checks. Manual testing/recovery is available through workflow input `monthly-macro-production`.

## Source and promotion contract

The monthly run fetches only:

- `nso-cpi`
- `nso-banking-activity`

Promotion is controlled by `config/monthly_macro_production_gate.json` and requires:

- `source_id = nso-vietnam`
- `readiness = ready-canonical`
- `evidence_status = verified`
- `period_type = month`
- one of the five allowlisted indicator IDs

The gate remains append-only and uses the existing logical key `(indicator_id, period_type, period)`.

## Repository auto-persistence contract

`scripts/persist_monthly_macro.py` applies `config/monthly_auto_persistence_policy.json` before any commit.

It blocks:

- record drops or mutation of an existing logical key;
- non-allowlisted indicators;
- non-monthly periods;
- non-final observations;
- non-verified evidence;
- non-NSO source IDs or source URLs outside `nso.gov.vn`;
- future periods;
- additions more than two months behind the current month;
- non-forward periods for an indicator;
- more than five additions in one run;
- stale production artifacts whose prior-record count no longer matches the repository;
- a changing run number that does not advance the shared `macro-candidate.yml` sequence.

A no-change run leaves repository files byte-for-byte unchanged and creates no git commit.

## Concurrent-write protection

The monthly path remains inside the same `macro-candidate.yml` workflow as daily FX/gold, so both paths share the workflow run-number sequence and top-level concurrency group. Before pushing, the persistence job compares current `origin/main` with the SHA captured at job start. If `main` changed meanwhile, the job stops instead of overwriting a newer repository state.

## Failure behavior

Source failure, missing observations, insufficient readiness, stale/future periods, conflicts and repository races all retain the last good committed state. The monthly run never writes empty replacements.

## Validation

`tests/test_phase4_5a_monthly_macro_auto_update.py` covers:

- exact five-indicator allowlist;
- schedule and targeted collector routing;
- full five-record synthetic append;
- idempotent replay/no-change behavior;
- rejection of unrelated daily data;
- narrow NSO source/host and freshness policy.

After upload, run:

`Actions → Macro Candidate Collector → Run workflow → monthly-macro-production`

On the current October 2026 baseline, September monthly statistics are already committed, so the expected result is normally `Added: 0` / `no-change` unless NSO has published a newer monthly period.
