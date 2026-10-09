# Market Data Coverage — Round 4D (2026-10-09)

## Screenshot accuracy review
In the Market > Pricing screenshot, eight independent projects' lower/upper asking-price estimates were linked by two smoothed lines. **This is not a time series** and implied interpolation between unrelated projects. Price comparison now uses a separate **vertical floating interval** for each project (one interval = one publisher-stated asking range), with project labels indicating apartment vs low-rise. Missing project-wide price ranges remain absent. The table's source-reported one-year change must not be presented as computed project history.

## Source-specific historical accumulation
- `data/mock/market/alternative-monthly-history.json` is an **independent OneHousing monthly apartment popular-asking series**, initialized with the already-reviewed Vinhomes Grand Park October 2026 baseline (54.47m VND/m², 36.81–331.19m VND/m²). This **does not create a second observation or count toward the Batdongsan project history**.
- No second independently verified OneHousing month is available yet, so **monthly trend readiness remains 0**.
- `data/candidate/market/alternative-price-review-queue.json` is discovered evidence only. Nothing enters reviewed history merely because it appears there.
- `config/market-alternative-reviewed-approvals.json` requires a separate human source audit: candidate ID, review date, verified publisher evidence and material review note.
- `scripts/market_alternative_history_release.py` verifies the exact publisher URL, original product segment, source-stated month, price/range text, stable baseline ID, no period duplicates, chronological append-only ordering and prior approved values.
- CI previews and checks every change. Once an explicit approval is committed, production may append only verified publisher month(s); the workflow does not alter developer ASP, Batdongsan market snapshots, Rever single listings, or CafeLand evidence.

## Numeric constraints unchanged
- 12 registered projects, 8 with portal aggregate ranges, 4 with only category reference, 18 portal snapshot records, 6 with 2 dated portal captures, **0 trend-ready portal histories**.
- OneHousing reviewed monthly series: **1 period**. Other alternative source cards: **7 source-specific price evidence records** across 6 projects.
- Historical 2023/2024 launch floors and expired unit listings remain source-dated references, not current spot prices.

## Next step — Round 4E
Find further monthly OneHousing pages/projects from explicitly dated, product-specific publisher output and expand `market-alternative-auto-targets.json` only after confirming they can be read reliably from GitHub Actions. Add at least two subsequent independent source months before rendering any OneHousing trend chart. Do not mix authors or price methods to satisfy a point count.
