# Phase 7.1 — Today / This Week / Top Developments

## Goal
Use the deterministic Phase 7.0 ranking engine to power the Home intelligence surfaces instead of separate date/importance sorting rules.

## Surfaces

### Today
- Uses the current Ho Chi Minh City calendar date.
- Includes only source-backed rankable items whose evidence date matches today.
- Keeps separate Market / Legal / Infrastructure / Macro cards.
- Within each module, higher attention score ranks first.
- Empty modules explicitly show no ranked updates today.

### What Changed
- Uses only structured change events from HistoryEngine.
- Ranks all change events with the shared engine.
- Shows the highest-attention change for each of Market / Legal / Infrastructure / Macro.
- This replaces the former "latest item per category" rule.

### This Week
- Uses a strict trailing 7-day window from the current HCMC date.
- Sorts by attention score, then evidence date, then stable ID.
- Shows up to six items.
- Caps each module at two items so one module cannot dominate the recap.

### Top Developments
- New Home surface.
- Uses a trailing 30-day window.
- Shows the top six ranked developments across all modules.
- Caps each module at two items to preserve cross-module balance.

## Rankable evidence
Home ranking candidates can include:
- structured HistoryEngine changes;
- source-backed Market / Legal / Infrastructure articles;
- official Legal issued/effective events;
- latest controlled Macro production observations.

Demo sources remain excluded by Phase 7.0 rules.

## UI semantics
Displayed labels use:
- attention tier;
- numeric attention score.

Example:
`High attention · 88`

This is **attention priority only**. It does not describe:
- positive or negative impact,
- project investment quality,
- investment recommendation,
- legal applicability,
- AI confidence.

## Determinism
Selection helpers live in:

`assets/js/intelligence-surfaces.js`

They implement:
- today;
- trailing windows;
- cross-module diversity caps;
- top-per-category selection.

The ranking itself remains in:

`assets/js/intelligence-ranking.js`

## Master roadmap
Phase 7.1 completes the rule-based intelligence surfaces required before the optional AI layer.

Next: **Phase 7.2 — Optional AI Analysis Layer**.
