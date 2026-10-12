# Phase 4L — Official M2 YTD automatic updates and release watchdog (2026-10-12)

## Purpose
Prevent M2 from remaining a manually seeded chart while GitHub's Macro candidate pipeline already automatically checks NSO banking releases. M2 YTD is growth of *tổng phương tiện thanh toán* compared with **the preceding December**; it is neither M2 stock nor year-over-year growth. The demo `m2-growth-yoy` is deliberately not promoted.

## Collection and publication
1. Existing scheduled `macro-candidate.yml` collects `nso-banking-activity` on the monthly NSO release window (days 1–10) without any new Worker secrets or Cron.
2. Its collector now returns M2 as a third verified observation only if the SAME dated banking report paragraph explicitly states `tổng phương tiện thanh toán tăng ... % so với cuối năm [previous year]`. It must be a March/June/September/December as-of quarter and a valid percentage.
3. The existing official NSO canonical source pool, frontend ID mapping and narrow automatic monthly persistence gate now permit `m2-growth-ytd` along with CPI, credit and funding. Maximum additions per pass rises from five to six.
4. The monthly gate additionally rejects mismatched quarter/as-of date, YoY instead of prior-December base, missing explicit quarter cadence, stale/future periods and nonofficial hosts. Existing immutable logical keys, staging verification and reconciliation remain in place.
5. If NSO does not report M2 or a scraper cannot substantiate the precise basis, **no M2 record is generated and the last valid period remains visible**. No guessing or interpolation.

The repository's 2024–2026 official historical archive remains untouched. Live canonical observations take precedence for the same indicator and period.

## Separate health monitoring
The new Maintenance dataset `macro-m2-ytd` distinguishes **a successful workflow** from **new official quarterly M2 data**. It checks existing verified NSO history plus newly published canonical M2 for the latest quarter after the **15th day of the second month following quarter-end** (operational reference aligned with national quarterly reporting handover, not a legal public release deadline).

- Status `review` and `release_status=missing-release` signal a period with no verified official record; these are follow-up prompts, not an assertion that NSO violated a statutory deadline.
- `release_expected_period`, `release_latest_period` and `release_note` explain the gap.
- On 2026-10-12, the last reviewed historical M2 is 2026-03, and 2026-06 is the most recent due quarter under this review threshold. A quarterly release missing from automation must not be labeled Healthy.
- On future verified data the release flag clears automatically without hand edits.

## QA
- `tests/test_macro_m2_auto_update.py`: official 2025-12 paragraph (14.98% from NSO), true previous-year-end basis, negative YoY/date/cadence fixtures, strict append-only automatic persistence. Synthetic values are solely isolated test fixtures, never production.
- `tests/test_macro_m2_health.py`: quarter reporting checkpoints, missing period review, no false reassurance from a green workflow or a fake YoY.
- Existing monthly CPI/credit and FX/gold tests remain active.

Original NSO reports:
- https://www.nso.gov.vn/du-lieu-va-so-lieu-thong-ke/2026/01/bao-cao-tinh-hinh-kinh-te-xa-hoi-quy-iv-va-nam-2025/
- https://www.nso.gov.vn/bai-top/2026/04/bao-cao-tinh-hinh-kinh-te-xa-hoi-quy-i-nam-2026/


## Phase 4L.1 — Weekly delayed-release recovery (12/10/2026)

**Why:** M2 YTD is quarterly and can be published substantially later than the monthly NSO CPI window. The original GitHub schedule only checked on days 1–10; a subsequent official M2 release would then remain missing until the next month. Furthermore, the shared 2-month backfill cutoff was too strict for a legitimate delayed quarterly release.

**Fix:** The existing `macro-candidate.yml` runs its same official NSO CPI/banking discovery and controlled publication gate at 10:55 ICT **every Monday** (UTC 03:55). The first-ten-days schedule remains intact. This is an additional real collection, not a health-only placeholder.

**Safety:** A verified `m2-growth-ytd` quarter can now be auto-persisted up to 8 months after the quarter's report month. The existing 2-month cutoff remains unchanged for CPI, credit growth and bank funding growth. An explicit as-of date, quarter-end month, comparison with the previous December, `nso-vietnam` source, and no logical-key overwrite remain required. Missing data cause `no-change`, not fabricated publication.

**Maintenance:** The quarter follow-up checkpoint is conservatively aligned with the 15th of the second month after quarter-end (e.g., Q2/2026 on 15 August, Q3/2026 on 15 November). The National Statistical Reporting rules concern submission of quarterly data, **not a legal guarantee that data will be publicly visible on that day**; the website's `Review` means investigate a missing official observation only. As of 12 October, the last reviewed NSO M2 quarter remains Q1/2026 and Q2/2026 remains a valid follow-up.

**Source method caution:** Independent reporting of 4.99% M2 growth for June 2026 appears alongside qualification about excluding securities. It has not been mixed into the NSO M2 YTD series until scope/definition and official source can be reconciled. Non-equivalent liquidity proxy data must stay separate.

**QA:** `tests/test_macro_m2_auto_update.py` now tests that a late 5-month verified quarter is accepted while a beyond-8-month quarter is rejected; `tests/test_macro_m2_health.py` verifies the conservative reporting dates. The original CPI tests verify their 2-month gate remains unchanged. `Phase 4K Macro Recovery Verification` is required before merge.
