# Phase 4.2I.5.1 — UI Consistency Cleanup

## Scope
Small frontend cleanup after the Phase 4.2I.5 visual review.

## Changes
1. Home demo rate cards now match the Macro demo source series:
   - 12M Deposit Rate change: `+0.05 ppt`
   - Average Lending Rate change: `0.00 ppt`
2. Home and Macro use the same English label: `Average Lending Rate`.
3. Vietnamese localization adds:
   - `Average Lending Rate` → `Lãi suất cho vay bình quân`
4. Chart.js legend labels now use the current UI language.
   - Example: `USD/VND Central Rate` → `Tỷ giá trung tâm USD/VND` in VI mode.
5. Charts rerender when the language is switched so canvas labels update immediately.
6. Cache-bust markers advance to `4.2I5.1`.

## Data safety
- No controlled production observation was edited.
- Production record count remains 8.
- No collector, promotion, persistence, or workflow file was changed.
