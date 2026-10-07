# Phase 4.4F — Production Hardening Baseline

## Purpose

Lock the accepted Phase 4.4E/4.4E.2 production behavior before Phase 4.5 expands automation to monthly and event-driven Macro datasets.

This phase does **not** broaden the production allowlist and does **not** change promotion/persistence business logic.

## Baseline contract

1. **Daily production scope remains narrow**
   - `usd-vnd-central-rate`
   - `sjc-gold-buy`
   - `sjc-gold-sell`
   - Automatic repository persistence requires the existing corroboration and safety gates.

2. **Append-only + idempotent repository behavior**
   - Historical logical keys cannot be mutated.
   - Re-running an already-persisted date produces `no-change` rather than a duplicate.
   - Source failure, disagreement or insufficient evidence retains the last good data.

3. **Data classification is explicit**
   - `data/mock/` is a legacy frontend path, not a statement that all records are mock.
   - Market, Legal and Infrastructure current registries are curated source-backed datasets.
   - Macro uses a controlled-production overlay from `data/processed/macro/observations.json`.
   - Explicit demo article/news/context records remain non-canonical.

4. **Freshness snapshot is synchronized**
   - The committed `data/state/update-status.json` is regenerated from repository data.
   - Runtime scheduled checks continue to build a read-only snapshot and do not change production data.

5. **CI/runtime is pinned for stability**
   - GitHub-hosted jobs use `ubuntu-24.04` instead of the moving `ubuntu-latest` label.
   - Official GitHub actions use Node.js-24-compatible majors.

## Deferred intentionally

- No rename/migration of the `data/mock/` directory in this phase.
- No broader automatic production allowlist.
- No backfill of synthetic history.
- No UI redesign.
- No automatic Legal / Infrastructure / Market publishing.

## Exit criteria

- Full pytest suite passes.
- Existing Phase 4.4E daily auto-publish test passes against the live repository baseline.
- Production hardening test confirms data-mode labels, action/runtime pins and update-status synchronization.
- The controlled daily workflow can be re-run without duplicate logical keys.
