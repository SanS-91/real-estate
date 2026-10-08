# Phase 7.2 — Optional AI Analysis Layer

## Goal
Add an AI-ready analysis layer above normalized canonical data without making AI part of collection, validation, ranking, or production truth.

## Default state
AI is **OFF by default**.

`config/ai-analysis.json` ships with:
- `enabled: false`
- `external_requests: false`
- `endpoint: null`
- same-origin-only remote policy

The Research Workspace remains fully functional when this file is disabled.

## Browser security
The browser configuration must never contain:
- API keys
- provider tokens
- authorization secrets
- passwords

If remote AI is ever enabled, the browser may call only a configured same-origin server/proxy endpoint. Provider credentials remain server-side.

## Canonical context pack
`assets/js/analysis-context-pack.js` builds a compact evidence pack from the existing Research subject context.

The pack deliberately separates:

### Direct evidence
- verified/research Market observations
- listing asking observations
- linked Infrastructure
- Infrastructure schedules
- source-backed Articles
- source-backed Events

### Contextual evidence
- Legal documents linked by the canonical topic/relevance model
- selected Macro observations

It also records the relationship semantics from the shared Intelligence Context model.

## Guardrails embedded in every pack
- canonical data only
- no missing-value inference
- Legal relevance is not Legal applicability
- listing asking is separate from verified/research pricing
- no production mutation

The generated prompt further requires source IDs / URLs for material claims when available and instructs the model to describe disagreements instead of silently averaging sources.

## Research actions
The optional Research panel supports context-pack generation for:
- Summarize
- Compare
- Explain Legal context
- Weekly brief
- Ask database

When AI is off, the user can still:
- Build analysis pack
- Copy prompt
- Copy context JSON

No data is sent anywhere.

## Optional remote adapter
`assets/js/optional-ai-analysis.js` provides a provider-neutral adapter contract.

A remote call is permitted only when:
1. AI is enabled,
2. external requests are enabled,
3. an endpoint is configured,
4. the endpoint satisfies the same-origin rule.

The adapter cannot mutate repository data.

## Architecture outcome
The original roadmap principle is preserved:

`Canonical data → deterministic intelligence/ranking → optional AI analysis`

not:

`AI → data truth`

With Phase 7.2 complete, the original Master Phase 7 exit criterion is satisfied while AI remains optional.
