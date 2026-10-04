# Phase 4.2G — Macro Frontend Integration v1

## Upload
Upload the contents of this patch to the repository root and overwrite matching files.

Changed files only:
- `macro.html`
- `assets/js/data-store.js`
- `assets/js/macro.js`
- `assets/js/localization-static.js`
- `assets/js/localization-dynamic.js`
- `data/mock/core/sources.json`

No workflow files are changed in this phase.
Do **not** replace or delete `data/processed/macro/observations.json` or `data/processed/macro/repository-publish.json`; those are the controlled production files already persisted by Phase 4.2F.

## Expected result
`macro.html` reads the controlled repository production data for the three approved CPI indicators:
- `cpi-yoy`
- `cpi-mom`
- `core-cpi-yoy`

For those indicators, the frontend uses production-only observations and removes the illustrative mock history, so canonical and demo history are never mixed within one CPI series.

All other macro indicators still use the existing v7.2.1 demo data.
If either processed production file is unavailable or fails the frontend gate, the page falls back safely to the v7.2.1 demo dataset.

After commit, open `macro.html` and check:
1. Header status shows `Canonical CPI · 3 verified records` (or Vietnamese equivalent).
2. CPI YoY shows `5.08%` for Sep 2026.
3. CPI MoM shows `0.62%` for Sep 2026.
4. Core CPI YoY shows `4.45%` for Sep 2026.
5. CPI source resolves to `National Statistics Office of Vietnam (NSO)`.
6. FX / Gold / Rates remain demo for now.
