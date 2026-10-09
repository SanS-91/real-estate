# Market Data Coverage — Round 4C (2026-10-09)

## Goal
Improve **data completeness and independent publisher coverage**, not redesign pages or inflate project ASP trends.

## Evidence added (source-reported listings, NOT transaction prices)
| Project | Product scope | Advertised unit asking | Original ad date | Publisher |
|---|---|---:|---|---|
| Izumi City | 164m² garden townhouse land basis | VND 68.5m/m² | 2026-05-26 | CafeLand |
| Essensia Parkway | 160m² semidetached villa land basis | VND 203m/m² | 2026-10-08 | CafeLand |
| The 9 Stellars | Alta Heights 100m² apartment | VND 62m/m² | 2025-01-05 | CafeLand |

Each record includes its **exact source URL, listing ID, original date, quoted asking rate, total asking price, stated area, property type, and confidence caveat**. Source totals and price-per-m² may be rounded by publishers.

### Important project-specific safeguards
- Izumi City: one **townhouse** at 68.5m/m² is not an apartment at Izumi nor its entire low-rise project price.
- Essensia Parkway: **160m² land basis** for a semidetached villa; do not confuse with advertisements quoting a 234m² construction area or with shophouses.
- The 9 Stellars: a **2025 expired apartment advertisement**, NOT an October 2026 market snapshot.
- Celesta Gold remains pending a defensible independently dated and product-specific observed price. Broker forecast/booking references are not considered actual observed aggregate prices.
- The original Batdongsan source access is still assisted and cannot be treated as automatically collected.

## Statistics that must NOT change
- 12 tracked projects; 18 Batdongsan capture rows; 8 projects with project-level aggregate asking ranges.
- 4 project/category-only reference records.
- 6 projects with two portal snapshots; 0 with comparable price trend-ready history.
- 4 existing OneHousing/Rever alternative references, now supplemented by 3 independent CafeLand single-property references.
- Additional source-reported listings do **not** repair the missing four project-wide aggregate prices.

## Pipeline
- `scripts/market_secondary_listing_gate.py` validates source URL, publisher, exact product, original source date, price, area and total.
- `scripts/market_secondary_listing_probe.py` checks pinned source access and evidence visibility **without generating dates or candidate prices**.
- `.github/workflows/market-secondary-listing-sources.yml` initially ran Tue/Fri, but after the first real GitHub-hosted run returned HTTP 403 on all three pages (2026-10-09), it runs **weekly Tuesday 10:50 ICT** to check whether access conditions change; CafeLand remains assisted-only until then. Only health JSON is persisted.
- Existing pricing/project detail panels use the same reference card layout and distinguish apartment/townhouse/villa.
- No chart averages, derived market changes, trend-ready flags, or gross-to-net conversions are inferred from individual ads.

## Next work package
Round 4D: qualify new source-authored dates or independent monthly category metrics for an auditable review/promotion path. Separate listing-index discovery from single-unit monitoring; never let a changing webpage without a new publisher reporting period create a synthetic historical observation.

## First post-merge production access audit (09 Oct 2026)

- Three URLs checked from GitHub Actions: **3/3 HTTP 403 (blocked)**.
- Price candidates created: **0**; production observation/history writes: **0**.
- The three already source-backed single-unit references remain visible, with an explicit blocked/assisted caveat.
- CafeLand is **not** counted as an automatically updating price source. The status is persisted in `data/state/secondary-listing-source-health.json`.
