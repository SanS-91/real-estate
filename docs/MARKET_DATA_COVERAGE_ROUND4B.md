# Market Data Coverage — Round 4B (Alternative Source Access & Historical Accumulation)

Implementation date: 2026-10-09. This work package follows Round 4A (PR #58) and **does not expand the frontend or project-wide price chart**.

## What now runs

- `.github/workflows/market-alternative-auto-probe.yml` executes on Tuesday and Friday at 03:35 UTC (10:35 Vietnam time), manually, and once after code changes on `main`.
- Tests 4 pinned publisher pages: OneHousing current Vinhomes Grand Park apartment category, Rever one-unit Vinhomes Grand Park listing, and 2 historical launch-price articles.
- Records source access and parsing classifications in `data/state/alternative-source-health.json`; captures a per-run report as a 30-day GitHub Actions artifact.
- A OneHousing month is eligible for **review queue only** if the source text explicitly states the project, month, popular asking price and range with coherent values.
- A Rever unit is eligible for **review queue only** when a later source-authored listing update date, 69m² unit context and exact advertised VND/m² value are present.
- `data/candidate/market/alternative-price-review-queue.json` preserves valid new-period candidates append-only; rechecks never rewrite the same candidate ID or erase the queue on a blocked fetch.

## Safety and comparability

1. `2023/2024` historic launch starting-price references are **frozen** and do not become October 2026 market observations.
2. OneHousing monthly modal/popular asking rates, Rever single-unit asking and Batdongsan portal asking ranges are **not equivalent** and never feed into the same project ASP chart.
3. Same-month publisher price edits can trigger a status needing review, **not** a new independent historical point.
4. HTTP 403/429/CAPTCHA, non-HTML content, publisher redirects, missing project labels and dynamically rendered pages that expose no verifiable price are marked blocked or unparseable. No source blocking is bypassed.
5. Candidate queueing is **not production promotion**. Review the original source, date, unit and scope before a separately guarded manual release. Any 0-new-candidate run means no new verified price was collected.

## Where to inspect

- Health JSON: `data/state/alternative-source-health.json`.
- Review queue: `data/candidate/market/alternative-price-review-queue.json`.
- GitHub Actions workflow: **Market Data Coverage Round 4B - Alternative Source Monitor**.
- Existing website: `market.html?view=pricing` keeps the unchanged Round 4A side-by-side alternative-source references.

## Next boundary (Round 4C)

After runner access has been observed over real scheduled runs, add provider-specific source refresh rules only where the sites support it, and a separately reviewed promotion path for monthly category series. Do not mark the price-trend readiness metric higher until genuinely independent and comparable periods are published.
