# Phase 4.2I.5 — Production Coverage & Frontend Consistency Audit

## Result
**PASS after consistency patch.** Repository production remains unchanged at **8 records**. The audit found one real frontend inconsistency: the Home Macro snapshot still used stale demo values even when controlled production existed. Phase 4.2I.5 fixes that Home-only gap without changing collectors, promotion, persistence, or processed production data.

## Repository integrity
- `record_count`: **8**
- `repository_publish`: **True**
- persistence: **6 prior + 2 added = 8 final**
- processed observations SHA-256: **MATCH** repository publish metadata
- source workflow: `macro-candidate.yml` run **#17**
- `frontend_publish` remains `false` by design; the controlled frontend reads repository-persisted observations through its explicit safety gate.

## Audit findings
1. **Macro page coverage: 8/8 production indicators covered.** All eight persisted records have a compatible frontend mapping and are reachable in the correct Macro detail view.
2. **Evidence labels are consistent.** Verified NSO records render as `CANONICAL`; corroborated FX/Gold records render as `CORROBORATED`.
3. **No synthetic history.** Once production exists for an indicator, its demo series is removed. Single-observation production series remain `Latest only`.
4. **Source registry: complete.** Every primary and corroborating source referenced by the eight production records exists in the frontend source registry.
5. **Home inconsistency found and fixed.** Before 4.2I.5, Home still showed demo USD/VND, Gold, Credit and CPI values and did not show Bank Funding Growth despite production being available. Home now reads the persisted production layer under a conservative gate, while Deposit/Lending cards remain explicitly demo.
6. **Home banner corrected.** It now says `Mixed data mode` instead of incorrectly claiming all Home values are mock data.

## Home controlled snapshot after patch
- USD/VND Central Rate → controlled `CORROBORATED`
- Domestic Gold Sell → controlled `CORROBORATED`
- 12M Deposit Rate → demo (no production record yet)
- Lending Rate → demo (no production record yet)
- Credit Growth YTD → controlled `CANONICAL`
- Bank Funding Growth YTD → controlled `CANONICAL`
- CPI YoY → controlled `CANONICAL`

`CPI MoM`, `Core CPI YoY`, and `Domestic Gold Buy` remain intentionally detail-only rather than being duplicated on the Home snapshot.

## Scope guard
No changes were made to:
- candidate collectors
- promotion policy
- persistence workflow
- `data/processed/macro/observations.json`
- `data/processed/macro/repository-publish.json`

See `PHASE4_2I_5_COVERAGE_MATRIX.csv` for the per-indicator matrix.
