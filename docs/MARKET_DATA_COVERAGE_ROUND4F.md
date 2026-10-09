# Market Data Coverage — Round 4F: Verified Subproject Monthly History

Date: 2026-10-09.

## State before release
- OneHousing **Lumière Boulevard** has a source-collector candidate explicitly labelled October 2026, modal asking **VND 73.74m/m²**, range **VND 57.00–100.19m/m²**. This is still **review-required**, not a published price point.
- OneHousing **Masteri Centre Point** has a September 2026 indexed-source reference, but the runner fetch of its beta URL returned **reachable-no-verifiable-metric**. Other indexed source versions have July/August/September month headers, so **never stamp the crawler date or infer October**.
- Both September 2026 subproject references were originally discovered in source indexing. They are **labelled indexed-source baselines** and are not equivalent to a separately rechecked live HTML observation.
- The OneHousing **parent Vinhomes Grand Park October** baseline remains in `alternative-monthly-history.json`, a separate series. Do not blend or average these values.

## New controls (4F)
1. `data/mock/market/alternative-subproject-monthly-history.json`: 2 distinct source-indexed September 2026 initial records, one per subproject, neither marked as independent live verification.
2. `scripts/market_subproject_candidate_recheck.py`: perform a new exact original-source URL request, enforce publisher project header, original month and all three price metrics; append a single status per workflow run to `data/state/alternative-candidate-verification.json`. A changed same-period price, inaccessible source or a stale month is **not an approval**.
3. `scripts/market_subproject_monthly_release.py`: requires matching source, subproject, product, verified month, **two separate successful matching GitHub Actions runs at least one hour apart**, plus an explicit review record in `config/market-subproject-reviewed-approvals.json`. Otherwise fail closed.
4. `.github/workflows/market-subproject-reviewed-history.yml`: after initial merge and on Tue/Fri 11:45 Vietnam time, perform source rechecks and record the operational status. No candidate is approved automatically. Only explicitly reviewed valid periods may be appended to the matching subproject series.
5. `scripts/market_alternative_auto_probe.py` reports non-sensitive parser flags for Masteri (exact publisher project/month present, modal price section/number/range present, login wall visible) without persisting copied full publisher HTML.

## User-facing Market Pricing
No layout changes: the recently compacted supplementary price references remain closed by default. History data and audit live in dedicated files until there are **independently verified comparable months**, not in the parent project price chart. All source citations and labelled original periods are retained.

## Release criteria
- An October Lumière candidate can only become a published separate series observation after two clean matching original-source rechecks at least one hour apart **and** an independent approval record matching the candidate and verification run IDs.
- If the source dynamically returns another month or a revised range, the candidate remains pending.
- Masteri still requires a readable source value. A page that only offers a login prompt does not qualify.
- **0** additional historic source periods may be claimed until the gate actually accepts a release; **0** project-wide Batdongsan trend-ready histories remain.

## Next step
Resolve Masteri source availability via a legitimate, publicly readable URL/version, and pursue second independent month captures for each subproject without conflating archive versions or publication/check dates.
