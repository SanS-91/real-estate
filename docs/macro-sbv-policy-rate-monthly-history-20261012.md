# Official SBV policy interest rate monthly history — 12 October 2026

**Source:** State Bank of Vietnam (SBV) annual report 2023, Appendix 1, "Interest Rates Announced by the SBV", https://www.sbv.gov.vn/documents/d/sbv_portal/590044

The original table states monthly *levels* of three administered rates, measured in percentage points per annum:

| Source period | Refinancing | Rediscount | SBV overnight lending facility |
|---|---:|---:|---:|
| 2022-12 | 6.0% | 4.5% | 7.0% |
| 2023-01 | 6.0% | 4.5% | 7.0% |
| 2023-02 | 6.0% | 4.5% | 7.0% |
| 2023-03 | 6.0% | 3.5% | 6.0% |
| 2023-04 | 5.5% | 3.5% | 6.0% |
| 2023-05 | 5.0% | 3.5% | 5.5% |

These 18 values are source-backed **monthly state snapshots**, not assertions that the rate changed on the 1st or last day of any month. `period_type=month`, `data_date=null`, `published_at=null` make that distinction explicit.

The currently verified live policy event on 19 June 2023 remains separate with `period_type=date` and the official effective date. Its three rates are refinancing 4.5%, rediscount 3.0%, SBV overnight lending 5.0%. This SBV overnight lending facility is **not** the floating interbank overnight market rate.

Historical storage: `data/processed/macro/historical-policy-monthly-observations.json`. This archive never overwrites live controlled policy events or enables unreviewed automatic history. The existing `macro-candidate.yml` policy event collector keeps checking current policy events under its two-source controlled publication threshold.

Macro charts distinguish a month-based historical snapshot from a precisely dated policy event. Source URL, source name, rate basis and validation status are retained.

**Regression:** `node tests/test_macro_policy_monthly_history.cjs` verifies all 18 official monthly values, official SBV source URL, required metadata, tampering rejection, plus blending with live policy events and 101 other historical observations. This test also runs in Phase 4K CI.
