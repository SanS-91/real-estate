# Upload — Phase 4.2I.4

Upload the patch into the repository root and overwrite matching files.

Changed runtime files:
- `macro.html`
- `assets/css/main.css`
- `assets/js/macro.js`
- `assets/js/localization-dynamic.js`
- `config/frontend_indicator_map.json`

QA contract:
- `tests/test_phase4_2i4_banking_frontend.py`

No workflow, collector, promotion, persistence, or processed production data file is changed.

After commit:
1. Do **not** run Macro Candidate Collector.
2. Do **not** run Macro Production Persistence.
3. Open `macro.html?view=overview&ui=4.2I4`.
4. Hard refresh once (`Ctrl+F5`) to bypass cached JS/CSS.
5. Confirm:
   - Credit Growth YTD = 10.89% · Sep 2026 · Canonical · NSO.
   - Bank Funding Growth YTD = 9.78% · Sep 2026 · Canonical · NSO.
   - Banking section includes both series.
   - A one-observation production series shows `Latest only` / no synthetic history.
   - Macro header shows `Controlled macro · 8 production records`.
