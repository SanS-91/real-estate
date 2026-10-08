# Phase 7.0 — Importance & Change Ranking Engine

## Goal
Create one deterministic rule-based engine for ranking **attention priority** of source-backed changes across Market, Legal, Infrastructure and Macro.

This is not:
- an investment score,
- a project quality score,
- positive/negative sentiment,
- an AI judgment.

## Components
Every rankable evidence/change row can receive up to 100 points from five transparent components:

1. **Source quality** — maximum 25
   - source priority 1 receives the highest weight
   - lower-priority research/media evidence receives fewer points
   - demo sources are excluded from production ranking

2. **Freshness** — maximum 20
   - recent evidence receives more points
   - old evidence remains available but receives zero freshness points after the configured horizon

3. **Event significance** — maximum 25
   - examples: Legal amendments/replacements, Infrastructure operation/schedule changes, Macro policy/rate changes, Market deltas

4. **Entity relevance** — maximum 15
   - explicit project, developer, region, infrastructure or Legal-document relations

5. **Change magnitude** — maximum 15
   - comparable percentage movements
   - schedule revisions
   - Legal amendment relations
   - explicit source-backed event importance

## Configuration
Rules live in:

`config/intelligence-ranking.json`

The browser engine is:

`assets/js/intelligence-ranking.js`

Rules can be loaded through:

`DataStore.getIntelligenceRankingRules()`

## Output
`rankOne(...)` adds:
- `attention_score`
- `attention_tier`
- `attention_label`
- component breakdown
- evidence date/source priority
- magnitude basis
- `ranking_semantics: attention-priority-only`

`rankAll(...)` sorts by:
1. attention score
2. evidence date
3. stable ID

This makes tied results deterministic.

## Tier labels
Current configuration:
- High attention
- Important
- Watch
- Context

Tier names describe review priority only.

## Provenance
Legal amendment change events now retain the official source ID and URL so they can participate in source-quality ranking without losing provenance.

## Principles
- Missing evidence produces zero points rather than inferred values.
- Different source types are not treated as equally authoritative.
- No component can exceed its configured cap.
- No category can become “important” merely because its wording sounds dramatic.
- Ranking does not say whether a change is good or bad for a project.
- AI is not used.

## Next
Phase **7.1 — Today / This Week / Top Developments** will use this engine to replace scattered date/importance sorting with consistent ranked intelligence surfaces.
