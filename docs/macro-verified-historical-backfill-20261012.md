# Verified Macro historical series — batch 1 (12 October 2026)

## Scope
The production Macro page now reads an **independent reviewed historical file**:
`data/processed/macro/historical-observations.json`.

The initial 2026 national CPI backfill includes:
- CPI year-on-year: January–August 2026 (8 observations)
- CPI month-on-month: January–August 2026 (8 observations)
- Core CPI year-on-year: January–June 2026 (6 observations)

**22 verified monthly facts** in addition to the previously stored September official data.
The core CPI July/August observations were intentionally left out of this batch pending a stable month-specific primary-document citation. A multi-month average cannot stand in for a monthly YoY rate.

Each record retains the original **observation month**, **publication date**, **official NSO release URL**, **indicator basis (YoY/MoM)**, `source_id=nso-vietnam`, and historical review metadata.

## Isolation from the daily pipeline
- Production collector remains append-only in `data/processed/macro/observations.json`.
- Historical NSO data is never sent through the daily FX/gold persistence path, whose safety policy forbids retroactive daily data.
- The Macro frontend merges validated historical records by exact `(indicator_id, period_type, period)` key. Live canonical data wins any duplicate key. Never blends illustrative demo history for indicators with real production data.
- Browser page shows current production count and independently verified historical count.
- This backfill does **not** create fake daily USD/VND or SJC gold quotes or invent intermediate CPI months.

## Ongoing cadence
New monthly CPI continues to be collected through the existing NSO monthly pipeline; subsequent scheduled runs update live production, not this historical archive. Additional years may be source-reviewed and appended to this file through PR plus CI; no unverified auto-backfill is permitted.

## Source trail
Cục Thống kê / National Statistics Office (NSO) monthly releases, 2026:
- 01/2026: https://www.nso.gov.vn/du-lieu-va-so-lieu-thong-ke/2026/02/chi-so-gia-tieu-dung-chi-so-gia-vang-va-chi-so-gia-do-la-my-thang-mot-nam-2026/
- 02/2026: https://www.nso.gov.vn/tin-tuc-thong-ke/2026/03/chi-so-gia-tieu-dung-chi-so-gia-vang-va-chi-so-gia-do-la-my-thang-hai-va-02-thang-dau-nam-2026/
- 03/2026: https://www.nso.gov.vn/du-lieu-va-so-lieu-thong-ke/2026/04/chi-so-gia-tieu-dung-chi-so-gia-vang-va-chi-so-gia-do-la-my-thang-ba-va-quy-i-nam-2026/
- 04/2026: https://www.nso.gov.vn/du-lieu-va-so-lieu-thong-ke/2026/05/chi-so-gia-tieu-dung-chi-so-gia-vang-va-chi-so-gia-do-la-my-thang-tu-va-4-thang-dau-nam-2026/
- 05/2026: https://www.nso.gov.vn/tin-tuc-thong-ke/2026/06/chi-so-gia-tieu-dung-chi-so-gia-vang-va-chi-so-gia-do-la-my-thang-nam-va-5-thang-dau-nam-2026/
- 06/2026: https://www.nso.gov.vn/tin-tuc-thong-ke/2026/07/chi-so-gia-tieu-dung-chi-so-gia-vang-va-chi-so-gia-do-la-my-thang-sau-quy-ii-va-6-thang-dau-nam-2026/
- 07/2026: https://www.nso.gov.vn/tin-tuc-thong-ke/2026/08/chi-so-gia-tieu-dung-chi-so-gia-vang-va-chi-so-gia-do-la-my-thang-bay-va-7-thang-nam-2026/
- 08/2026: https://www.nso.gov.vn/tin-tuc-thong-ke/2026/09/chi-so-gia-tieu-dung-cpi-chi-so-gia-vang-va-chi-so-gia-do-la-my-thang-tam-va-8-thang-nam-2026/
