# GitHub Actions — Candidate Mode

## Purpose

The scheduled workflow runs the live Macro collector without publishing to the production website.

**Hard guardrails**

- `production_publish` is fixed to `false`.
- Workflow permission is `contents: read`; it cannot commit or alter the repository.
- Output is uploaded as a GitHub Actions artifact only.
- Raw fetched HTML is not included in the artifact or Git history.
- Existing frontend files and `data/processed` are untouched.

## Schedule

GitHub cron uses UTC:

- `00:15 UTC` every day = approximately `07:15 Asia/Ho_Chi_Minh`.
- `09:15 UTC` Monday–Friday = approximately `16:15 Asia/Ho_Chi_Minh`.

GitHub scheduled workflows may start later than the exact cron minute. This is acceptable for candidate monitoring and is not treated as a real-time feed.

## Run flow

1. Checkout repository.
2. Install Python dependencies.
3. Restore prior candidate/state cache if available.
4. Run parser/discovery tests.
5. Run offline end-to-end candidate pipeline test.
6. Fetch configured live sources.
7. Parse and normalize records.
8. Validate schemas and safety gates.
9. Resolve `ready / evidence-only / missing` per indicator.
10. Upload candidate outputs as an artifact retained for 30 days.

## Candidate artifact contents

- `observations.json`
- `research-evidence.json`
- `publish-readiness.json`
- `source-health.json`
- `run-report.json`
- `candidate-summary.csv`
- rejected build output when safety gates fail

## Source failures

A single source failure does not erase prior good candidate history. Mandatory-source failures mark the run `degraded`; optional-source failures are recorded as degraded evidence. Schema or candidate safety failures block replacement and write the proposed build to `data/rejected/macro/<run_id>/`.

## Promotion

There is deliberately **no automatic promotion to `data/processed`** in Phase 4.2B. Promotion will be designed only after candidate runs have been reviewed over multiple cycles.
