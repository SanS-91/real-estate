from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
js=(ROOT/"assets/js/market.js").read_text(encoding="utf-8")
css=(ROOT/"assets/css/main.css").read_text(encoding="utf-8")

assert "source: ''" in js
assert "'q','region','developer','segment','status','sort','source'" in js
assert "function marketSourceLabel(sourceId)" in js
assert "function preferredMarketSource(rows)" in js
assert "data-filter=\"source\"" in js
assert "Source Comparison" in js
assert "Values from different research houses are not averaged or merged." in js
assert "Source methodologies may differ. Comparison is side-by-side only; no cross-source averaging is performed." in js
assert "row.source_id === state.source ? 'is-selected-source' : ''" in js
assert ".market-source-toolbar" in css
assert ".data-table--market-source-comparison tr.is-selected-source td" in css
assert "function formatMarketMetric(row, field)" in js
assert "row.new_supply_lower_bound" in js
assert "≈ / > retain the wording precision published by the source." in js

import json
cand=json.loads((ROOT/"data/candidate/market/observations.json").read_text(encoding="utf-8"))["data"]
by={x["segment_ids"][0]:x for x in cand}
assert by["apartment"]["new_supply"] is None
assert by["apartment"]["new_supply_lower_bound"]==1300
assert by["apartment"]["absorption_rate"]==0.31
assert by["landed"]["new_supply"]==1700
assert by["landed"]["sales_units"]==870
assert by["landed"]["metric_qualifiers"]["new_supply"]=="approx"
assert by["landed"]["metric_qualifiers"]["absorption_rate"]=="approx"

print("Phase 5.5F4 multi-source Supply & Sales UI tests PASS")
