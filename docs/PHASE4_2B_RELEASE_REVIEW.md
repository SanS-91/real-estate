# Phase 4.2B Release Review — Live Hardening + GitHub Actions Candidate Mode

## Scope

This phase changes **collector infrastructure only**. It does not change v7.2.1 frontend files and does not replace mock data.

## Added / hardened

- Config-driven live source registry for collectors.
- Retry/backoff, response-size limits and request metadata capture.
- NSO/VOV/Vietcap discovery helpers.
- Direct SBV candidate endpoint isolated behind source-health reporting.
- Atomic candidate replacement.
- Historical candidate merge by stable observation ID.
- Source-health and run-report outputs.
- Candidate safety gates and rejected-build quarantine.
- Offline parser/discovery tests.
- Offline end-to-end candidate pipeline test.
- Scheduled GitHub Actions workflow in read-only repository mode.
- Candidate output is uploaded as an artifact; no repository commit and no production publish.

## Explicitly not implemented

- No writes to `data/processed`.
- No frontend integration.
- No automatic canonical promotion.
- No AI summarization.
- No repository write permissions in the workflow.
- No raw-source HTML stored in GitHub artifacts.

## Promotion gate for next phase

Before any real candidate data is used by the website, review at least several scheduled runs for:

1. source stability;
2. parser stability;
3. dates/period semantics;
4. duplicate behavior;
5. official-vs-secondary evidence handling;
6. source failures and recovery;
7. unexpected outliers.
