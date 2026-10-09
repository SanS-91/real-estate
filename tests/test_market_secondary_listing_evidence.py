"""Coverage round 4C must not confuse individual advertisements with project-wide prices."""
from __future__ import annotations
import copy
import importlib.util
import json
from datetime import date
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("secondary_listing_gate",ROOT/"scripts/market_secondary_listing_gate.py")
gate=importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
data=json.loads((ROOT/"data/mock/market/secondary-listing-evidence.json").read_text(encoding="utf-8"))
rows=data["data"]
projects={x["id"] for x in json.loads((ROOT/"data/mock/market/projects.json").read_text(encoding="utf-8"))["data"]}
sources={x["id"] for x in json.loads((ROOT/"data/mock/core/sources.json").read_text(encoding="utf-8"))["data"]}
assert data["record_count"]==len(rows)==3
assert {r["project_id"] for r in rows}=={"izumi-city","essensia-parkway","the-9-stellars"}
assert all(r["metric_type"]=="single-listing-asking-price-per-sqm" for r in rows)
assert not gate.validate(rows,projects,sources,date(2026,10,9))
for i in range(3):
    for field,bad in [
        ("source_url","https://invalid.example/price"),("value_vnd_per_m2",30_000_000),
        ("listed_area_sqm",1000),("project_id","akari-city"),
        ("source_publication_date","2026-10-10"),("metric_type","project-asp")]:
        broken=copy.deepcopy(rows);broken[i][field]=bad
        assert gate.validate(broken,projects,sources,date(2026,10,9)),(i,field)
data_store=(ROOT/"assets/js/data-store.js").read_text(encoding="utf-8")
market=(ROOT/"assets/js/market.js").read_text(encoding="utf-8")
assert "getSecondaryListingEvidence" in data_store
assert "data.secondaryListingEvidence" in market
assert "secondaryListingEvidence: payloadData(secondaryListingEvidence)" in market
assert "projectIds.includes(item.project_id)" in market
assert "productLabels" in market
assert "row.subproject_name || productLabels[row.asset_type]" in market
assert "listingPriceRows(filteredProjects)" in market and "listingRangeChartData(filteredProjects)" in market
assert "data.secondaryListingEvidence" not in market[market.index("function listingRangeChartData"):market.index("function priceLayerControls")]
listing=json.loads((ROOT/"data/mock/market/listing-observations.json").read_text(encoding="utf-8"))
scope=json.loads((ROOT/"data/mock/market/listing-scope-evidence.json").read_text(encoding="utf-8"))
assert listing["record_count"]==18
assert scope["record_count"]==4
assert len({r["project_id"] for r in rows})==3
print("PASS: 3 source-priced individual units, 3 projects, unchanged 18 portal observations and 4 scoped references.")
