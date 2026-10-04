# Phase 4.2B QA Report

Date: 2026-10-04

## Automated offline checks

- Parser tests: PASS
- Discovery helper tests: PASS
- End-to-end fixture candidate pipeline: PASS
- Candidate schema validation: PASS
- Python compile check: PASS
- JSON parse check: PASS (17 JSON files)
- Fixture run status: PASS
- Fixture observations: 7
- Fixture research records: 1
- Fixture production_publish: false

## Safety checks

- Workflow permission: `contents: read`
- No `git commit` / `git push` in workflow
- No writer to `data/processed`
- Candidate-only pipeline rejects any non-candidate mode
- Raw HTML excluded by `.gitignore` and artifact configuration
- Empty candidate blocked
- Large candidate record-count drop blocked
- Schema failure quarantined under `data/rejected/macro/<run_id>`
- Source failure does not delete prior candidate history

## Live-source note

The environment used to build this review pack cannot execute the collector against the public internet. Live endpoint availability therefore remains a GitHub Actions runtime check and is explicitly surfaced in `source-health.json`. Parser behavior itself is tested against deterministic fixtures.

## Expected first live review

After the first GitHub Actions run, review:

1. `source-health.json`
2. `run-report.json`
3. `candidate-summary.csv`
4. `publish-readiness.json`
5. any quarantined build under `data/rejected`

No website data should be promoted from the first live run.
