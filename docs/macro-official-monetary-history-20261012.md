# Macro History — NSO monetary snapshots & official SBV rate ranges (12/10/2026)

## Definitions: do not mix distinct concepts

- `m2-growth-ytd`: growth (%) of *tổng phương tiện thanh toán* (broad money M2) relative to the previous December. This is **NOT M2 YoY**, **NOT** a money-stock value in VND, and **NOT** the same as credit outstanding growth. NSO defines total means of payment as M2: https://www.nso.gov.vn/du-lieu-dac-ta/2023/01/htcttkqg-tong-phuong-tien-thanh-toan/
- `credit-growth-ytd`: growth of economy-wide credit relative to preceding December (NSO releases).
- `bank-funding-growth-ytd`: growth of capital mobilization by credit institutions relative to preceding December (NSO releases).
- `deposit-rate-vnd-6-12m-low/high`: the **range** of domestic commercial-bank average VND deposit rates for 6-to-12-month tenors from the monthly State Bank of Vietnam (SBV) rate bulletin.
- `lending-rate-vnd-average-low/high`: the **range** of domestic commercial-bank average VND rates on new AND outstanding loans; not the priority-sector short-term policy-controlled lending rate.
- Month-like period `YYYY-MM` is the **statistical report period**, not a statement that the official figure was observed on the last calendar day. Every NSO record retains the actual `as_of_date` / `data_date`.

## Published archive — 33 additional observations

The new standalone file is `data/processed/macro/historical-monetary-observations.json`, with 7 NSO reporting periods × 3 money/credit metrics (21 points) and 3 SBV bulletin months × 4 rate-bound components (12 points).

| NSO reporting period | As-of date | M2 YTD | Funding YTD | Credit YTD | Official source |
|---|---|---:|---:|---:|---|
| 2024-09 | 2024-09-27 | 5.10% | 4.79% | 8.53% | https://www.nso.gov.vn/bai-top/2024/10/bao-cao-tinh-hinh-kinh-te-xa-hoi-quy-iii-va-9-thang-nam-2024/ |
| 2024-12 | 2024-12-25 | 9.42% | 9.06% | 13.82% | https://www.nso.gov.vn/bai-top/2025/01/bao-cao-tinh-hinh-kinh-te-xa-hoi-quy-iv-va-nam-2024/ |
| 2025-03 | 2025-03-25 | 1.99% | 1.36% | 2.49% | https://www.nso.gov.vn/du-lieu-va-so-lieu-thong-ke/2025/04/bao-cao-tinh-hinh-kinh-te-xa-hoi-quy-i-nam-2025/ |
| 2025-06 | 2025-06-26 | 7.09% | 6.11% | 8.30% | https://www.nso.gov.vn/bai-top/2025/07/bao-cao-tinh-hinh-kinh-te-xa-hoi-quy-ii-va-6-thang-dau-nam-2025/ |
| 2025-09 | 2025-09-25 | 10.61% | 9.74% | 13.00% | https://www.nso.gov.vn/bai-top/2025/10/bao-cao-tinh-hinh-kinh-te-xa-hoi-quy-iii-va-9-thang-nam-2025/ |
| 2025-12 | 2025-12-22 | 14.98% | 13.68% | 17.65% | https://www.nso.gov.vn/du-lieu-va-so-lieu-thong-ke/2026/01/bao-cao-tinh-hinh-kinh-te-xa-hoi-quy-iv-va-nam-2025/ |
| 2026-03 | 2026-03-24 | 1.04% | 0.44% | 2.15% | https://www.nso.gov.vn/bai-top/2026/04/bao-cao-tinh-hinh-kinh-te-xa-hoi-quy-i-nam-2026/ |

Note: 2024-12 and 2025-12 figures are **as of 25 Dec / 22 Dec**, NOT full 31 Dec actuals. If superseding final annual values become available, they must be recorded with their correct as-of and vintage rather than silently replacing the reported snapshots.

| SBV month | Deposit 6–12m VND p.a. | Average VND loan p.a. | SBV canonical source |
|---|---|---|---|
| 2025-05 | 4.5–5.5% | 6.6–8.9% | https://sbv.gov.vn/documents/d/sbv_portal/lai-suat-thang-5-2025-2-.pdf?download=true |
| 2025-06 | 4.5–5.5% | 6.5–8.8% | https://www.sbv.gov.vn/documents/20117/0/Lai%2Bsuat%2Bthang%2B6.2025%2B%281%29.pdf/fb44102c-70d5-4913-1c5c-b45b837b7741?t=1753083536901 |
| 2025-07 | 4.6–5.5% | 6.5–8.9% | https://sbv.gov.vn/documents/20117/2063149/Lai%20suat%20thang%207.2025.pdf.pdf/a680b271-5620-28e0-31a3-9ce6a0f5ce0b |

The release day is not printed unambiguously in the rate-bulletin PDFs; `published_at=null` and `source_release_period=YYYY-MM` deliberately avoid inventing a day.

## Publication safety

- History is **separate** from the automated live `data/processed/macro/observations.json` (existing 24 observations) and its source-run metadata.
- Exact `(indicator_id, period_type, period)` keys cannot shadow live canonical records; on any later overlap live values always win.
- Frontend accepts monetary history only when source domain is official NSO/SBV, observation basis and cutoff are consistent, period/units are correct, and verification flag is present. It preserves NSO reporting dates.
- 4 SBV low/high components per period produce two **paired range charts**, not invented averages; primary official SBV ranges display as **Canonical**.
- History is reviewed in a PR, not faked by quarterly interpolation. Existing monthly credit/funding candidate pipelines keep running automatically; M2 YTD quarterly history is **not yet** an auto-populated current-period series. Automatic incremental M2 collection is the next dedicated integration.
- For 2024–2026 `ALL` range shows all source-verified periods; `1Y` may show fewer since archived as-of records are quarterly.
- The historical dates and rates remain source-period-specific. A rate for 2025-07 must not be described as the current rate in 2026.

## Validation

`python tests/test_macro_official_monetary_history.py`

`node tests/test_macro_monetary_history_ui.cjs`

Both run automatically inside `Phase 4K Macro Recovery Verification` when the archive or frontend changes. These tests check exact values, basis, as-of date, official source URL, duplicate keys, immutable canonical baseline and range pairing.
