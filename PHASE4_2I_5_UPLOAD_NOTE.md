# Phase 4.2I.5 Upload Note

Upload the contents of the patch ZIP to the **repository root**, preserving folders and overwriting matching files.

## Files changed
- `index.html`
- `assets/css/main.css`
- `assets/js/home.js`
- `assets/js/localization-static.js`
- `assets/js/localization-dynamic.js`
- `config/frontend_indicator_map.json`
- `tests/test_phase4_2i4_banking_frontend.py`
- `tests/test_phase4_2i5_frontend_consistency.py`
- audit / QA documentation

## After commit
No Candidate Collector or Production Persistence run is required. This is a frontend consistency patch only.

Open **Home** and use `Ctrl + F5`. Check that the Macro snapshot shows controlled values for USD/VND, Gold Sell, Credit Growth YTD, Bank Funding Growth YTD and CPI YoY, while Deposit and Lending remain demo.
