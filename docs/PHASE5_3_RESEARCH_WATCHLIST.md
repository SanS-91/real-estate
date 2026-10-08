# Phase 5.3 — Saved Research Watchlist & Update Inbox

## Goal
Allow users to save Project, Region or Developer research subjects in the browser and surface newly linked source-backed activity without introducing a backend or mutating canonical data.

## Storage
- watchlist subjects are stored in localStorage
- reviewed evidence IDs are stored separately in localStorage
- data is browser-local and does not sync across devices

## Update logic
- saving a subject records the currently linked evidence IDs as the baseline
- the inbox shows later unseen evidence IDs, not simply items with a newer calendar date
- backdated newly-added evidence is therefore still detectable
- demo-source articles/events are excluded

## Safety
- no repository writes
- no canonical data changes
- no external account data
- no inferred facts or synthetic ranking
