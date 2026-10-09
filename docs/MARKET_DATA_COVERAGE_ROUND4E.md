# Market Data Coverage — Round 4E (2026-10-09)

## Objective
Expand reliable source **coverage**, rather than drawing price growth from unrelated projects or artificially cloning recent page checks into historical price observations.

## New OneHousing publisher-specific apartment references
Two nested apartment developments inside Vinhomes Grand Park are now tracked as **subprojects** (not new project registry entries).

| Subproject | Source-stated period | Modal apartment asking (million VND/m²) | Advertised range (million VND/m²) | Original URL |
|---|---|---:|---:|---|
| Lumière Boulevard | 2026-09 | 73.40 | 57.44–100.06 | https://onehousing.vn/phan-tich/du-an/can-ho-chung-cu-du-an-Lumiere-Boulevard.34 |
| Masteri Centre Point | 2026-09 | 70.90 | 53.06–224.87 | https://beta.onehousing.vn/phan-tich/du-an/can-ho-chung-cu-du-an-Masteri-Centre-Point.53 |

These September figures were found in indexed OneHousing project source results. **Important provenance caveat:** a separately indexed or freshly retrieved version of either URL may expose another source-reported month (e.g. July/August). The values above are **historical source-labelled references**, not confirmation that the currently accessible page still reports September data. Future runner probes record the period actually returned and cannot add a check-date snapshot.

The two source records are in `data/mock/market/alternative-subproject-monthly-evidence.json`, presented only as existing `Nguồn giá đối chiếu` cards under the Vinhomes Grand Park project, preserving each subproject name, source, period and method. The two price measures are **modal asking price and listing range, not transaction ASP**.

## Automated monitoring and quality controls
- `config/market-alternative-auto-targets.json`: now **6** source pages; 3 independent OneHousing monthly apartment series (Vinhomes Grand Park itself, Lumière Boulevard, Masteri Centre Point); 1 Rever individual unit; 2 frozen historical articles.
- `scripts/market_alternative_auto_probe.py` normalizes publisher header accents but enforces the **exact named source project**, distinct URL, original baseline ID, asset type and publisher-month. It checks source month, not runner date. Newer publisher periods create **review-required candidates only** in an append-only queue.
- `scripts/market_onehousing_subproject_gate.py` checks quoted source month/price/range, label, URL and baseline integrity. It explicitly rejects source/project/scope mixing.
- GitHub Actions runs Tue/Fri, retains access statuses and candidate reports; no access bypass. The current site shows the 2 source references without a historical time-series chart.

## Invariants
- **12** registered parent projects; **8** portal aggregate priced projects, **4** category-only references, **18** existing portal captures, **6** parent projects with two portal snapshots.
- **0** trend-ready Batdongsan portal project price series.
- The already-reviewed OneHousing Vinhomes Grand Park monthly history remains **1** October 2026 period; the two new September subproject references are separate **one-period baselines**, not new observations of this parent series.
- No artificial parent ASP, delta, transaction estimate or absent period. No historical price change calculated by comparing unrelated subprojects.

## Remaining gap (Round 4F)
Confirm the *same* OneHousing subproject returns independently authored later months on multiple scheduled runner checks; obtain source-bound source captures and explicit approvals before adding a second comparable historical point. Broaden standalone tracked project coverage only after matching sources become accessible and source metric definitions agree.
