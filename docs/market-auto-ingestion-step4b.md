# Step 4B — Market Data Auto-Ingestion

## Automatic daily run

The Market Source Candidate Collector workflow runs at 02:30 UTC every day. It fetches sources and writes verification reports as GitHub Actions artifacts.

- Nam Long official news: discover article links from the publisher's news index. Verify original article URL, article-visible published date, meaningful excerpt and project references. Strictly verified new articles append to data/mock/articles/articles.json.
- CBRE HCMC quarterly residential supply: discover quarter-specific releases from the official CBRE insights index. Verify the quarter in the article title, publication date, release identity and exact numeric source phrase. Verified apartment/landed new-supply metrics append to data/mock/market/observations.json.
- Cushman, JLL and Savills remain candidate/manual-review-only when the source page lacks a unique report identity, quarter or date. Never invent ASP/absorption/sales figures.

## Safety

- Never use the HTTP fetch date as a publication date.
- Reject ambiguous or missing reporting quarters, redirected article URLs and source-date mismatches.
- Historical market series are append-only. Conflicts do not overwrite existing periods.
- The PR collector workflow performs an isolated live-data production simulation but never pushes to main.
- Only a collector run on main can commit the two allowed production JSON files.
- If no new verified article or metric exists, production files remain unchanged.
- Every scheduled run produces downloadable provenance, freshness and promotion reports.

## Subsequent roadmap work

Expand official and research source coverage, add validated ASP/absorption/sales series, historical PDFs and historical listing-price snapshots. Fixture-mode source-state entries do not prove genuine live collection.
