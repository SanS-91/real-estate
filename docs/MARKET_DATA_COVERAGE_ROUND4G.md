# Market Data Coverage — Round 4G: Unattended monthly price collection & release (2026-10-09)

## Persistent automation, not a one-off scrape
A single GitHub Actions workflow `market-auto-monthly-prices.yml` is the sole scheduled writer of OneHousing monthly project source data. It runs **every day at 09:35 and 13:45 ICT** (02:35 and 06:45 UTC). Every run does the whole sequence:

1. Fetch six source pages (3 OneHousing apartment monthly series; 1 Rever unit monitor; 2 historic articles) and discover only **publisher-authored** newly dated months.
2. Append new month/type/project-specific candidate evidence to the durable queue. Repeated scans do not create duplicate candidates.
3. Re-fetch exact publisher sources for queued subproject months; the OneHousing Masteri Centre Point beta page can fall back to its canonical `onehousing.vn` page **with identical project slug and ID** if the beta page is blank/JS-login-walled.
4. Record check evidence with the GitHub run ID, source host, HTTP response, captured month and a stable content hash; do not confuse the scan date with the publisher's price period.
5. Automatically publish to each subproject's isolated history **only** after the **two most recent separate source rechecks match exactly**, are at least one hour apart, the publisher/project name and rate/range agree, and the modal rate moves <= 30% versus its preceding same-series month. Mark `review_status=automated-source-verified` and capture both run IDs. This is technical source verification, not human sign-off and not transaction/ASP verification.
6. Commit source status, candidate queue, two-run verification and history **together**, so future runs and the GitHub Pages website use the saved state.
7. The existing compact **Giá tham khảo bổ sung** display automatically uses the latest `automated-source-verified` month for Lumière Boulevard or Masteri Centre Point. If no new month passes, the old source-labelled reference remains; no new card or confusing average is created.

## Failure policy
- No new source-authored month: retain old data.
- Source portal login wall, HTTP 403, mismatched project or missing modal/range: log the issue; never guess or publish.
- Two checks disagree, <1 hour apart, same run ID or outdated source: do not publish.
- Unexpected rate change above 30%: log for later source review; never auto-publish.
- Previously published month: keep immutable; do not overwrite even if site modifies the page.
- September 2026 subproject baselines remain **source-indexed** references, never retroactively labelled live-verified.
- No one-off manual workflow triggering, code edits or individual human approval is necessary for an ordinary valid new month.

## Isolation
- Vinhomes Grand Park parent OneHousing popular asking and Batdongsan range are independent metrics.
- Individual Rever/CafeLand listings and historical launch prices are not monthly subproject price data.
- Automatic changes to subproject history do **not** change 12 registered parent projects, 18 Batdongsan observations, or parent ASP/price-trend charts.

## Monitoring
- See GitHub Actions: **Market 4G - Automatic Monthly Source Price Pipeline** and its execution summary.
- `data/state/alternative-candidate-verification.json` gives last independent checks.
- `data/state/alternative-source-health.json` gives publisher access statuses, including fallback origin for Masteri.
- `data/mock/market/alternative-subproject-monthly-history.json` gives published isolated history and verification runs.
- Existing older Round 4B/4F workflows remain available for manual QA, **but no longer have overlapping schedules**.

This workflow is subject to source availability and GitHub Actions schedule delays. Reliable scheduling and automatic publication cannot guarantee a source publishes data every month.
