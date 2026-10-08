# Phase 7.0A — Ranking Contract Audit

## Purpose
Phase 7.0 is already implemented in production. This small hardening step audits the existing ranking contract rather than re-implementing it.

## Contract under audit
The ranking engine estimates **attention priority only**.

It does not represent:
- investment attractiveness
- project quality
- positive or negative impact
- AI judgment

## Score model
The configured maximum score is 100, split across five capped components:

- Source quality — 25
- Freshness — 20
- Event significance — 25
- Entity relevance — 15
- Change magnitude — 15

The audit asserts that component weights sum to the configured maximum score and that no configured rule exceeds its component cap.

## Source-quality contract
Active production sources must use the controlled source-priority scale:

1. official / strongest canonical source
2. first-party / operator / developer / financial institution
3. research / consultancy
4. media / lower-priority evidence

Demo sources remain excluded from production ranking.

## Freshness contract
Freshness bands must:
- be ordered by age
- decrease monotonically in points
- end with an open-ended zero-point band

Missing dates receive zero freshness points.

## Tier contract
Tiers must be ordered from highest to lowest threshold, have unique IDs, and end at score 0.

Current semantic tiers:
- High attention
- Important
- Watch
- Context

## Runtime output contract
Every ranked row must expose:

- `attention_score`
- `attention_tier`
- `attention_label`
- `ranking_components`
- `ranking_evidence`
- `ranking_semantics = attention-priority-only`

Missing evidence must produce zero points for the relevant component rather than inferred values.

Exact score/date ties must remain deterministic through stable-ID ordering.

## Scope
This phase does not:
- change weights
- change score output
- modify Home surfaces
- modify ranking production data
- change AI behavior

It only adds contract and runtime audits so later calibration work cannot silently break ranking semantics.
